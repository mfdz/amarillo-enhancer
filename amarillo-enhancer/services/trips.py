from ..models.gtfs import GtfsTimeDelta, GtfsStopTime
from amarillo.models.Carpool import MAX_STOPS_PER_TRIP, Carpool, Weekday, StopTime, PickupDropoffType, Driver, RidesharingInfo
from ..services.config import config
from ..services.gtfs_constants import *
from ..services.routing import RoutingService, RoutingException
from amarillo_stops.stops import is_carpooling_stop
from shapely.geometry import Point, LineString, box
from geojson_pydantic.geometries import LineString as GeoJSONLineString
from datetime import datetime, timedelta
import numpy as np
import os
import json
import logging

logger = logging.getLogger(__name__)
class TripTransformer:
    REPLACE_CARPOOL_STOPS_BY_CLOSEST_TRANSIT_STOPS = True
    REPLACEMENT_STOPS_SERACH_RADIUS_IN_M = 1000
    SIMPLIFY_TOLERANCE = 0.0001

    router = RoutingService(config.graphhopper_base_url)

    def __init__(self, stops_store):
        self.stops_store = stops_store

    def _trip_id(self, carpool):
        return f"{carpool.agency}:{carpool.id}"

    def _replace_stops_by_transit_stops(self, carpool, max_search_distance):
        new_stops = []
        for carpool_stop in carpool.stops:
            new_stops.append(self.stops_store.find_closest_stop(carpool_stop, max_search_distance))
        return new_stops

    def enhance_carpool(self, carpool):
        if self.REPLACE_CARPOOL_STOPS_BY_CLOSEST_TRANSIT_STOPS:
            carpool.stops = self._replace_stops_by_transit_stops(carpool, self.REPLACEMENT_STOPS_SERACH_RADIUS_IN_M)
 
        path = self._path_for_ride(carpool)
        lineString_shapely_wgs84 = LineString(coordinates = path["points"]["coordinates"]).simplify(0.0001)
        lineString_wgs84 = GeoJSONLineString(type="LineString", coordinates=list(lineString_shapely_wgs84.coords))
        virtual_stops = self.stops_store.find_additional_stops_around(lineString_wgs84, carpool.stops) 
        if not virtual_stops.empty:
            virtual_stops["time"] = self._estimate_times(path, virtual_stops['distance'])
            logger.debug("Virtual stops found: {}".format(virtual_stops))
        if len(virtual_stops) > MAX_STOPS_PER_TRIP:
            # in case we found more than MAX_STOPS_PER_TRIP, we retain first and last 
            # half of MAX_STOPS_PER_TRIP
            virtual_stops = virtual_stops.iloc[np.r_[0:int(MAX_STOPS_PER_TRIP/2), int(MAX_STOPS_PER_TRIP/2):]]
            
        trip_id = f"{carpool.agency}:{carpool.id}"
        stop_times = self._stops_and_stop_times(carpool.departureTime, trip_id, virtual_stops)
        
        enhanced_carpool = carpool.copy()
        enhanced_carpool.stops = stop_times
        enhanced_carpool.path = lineString_wgs84
        return enhanced_carpool

    def _convert_stop_times(self, carpool):

        stop_times = [GtfsStopTime(
                self._trip_id(carpool), 
                stop.arrivalTime, 
                stop.departureTime, 
                stop.id, 
                seq_nr+1,
                STOP_TIMES_STOP_TYPE_NONE if stop.pickup_dropoff == PickupDropoffType.only_dropoff else STOP_TIMES_STOP_TYPE_COORDINATE_DRIVER, 
                STOP_TIMES_STOP_TYPE_NONE if stop.pickup_dropoff == PickupDropoffType.only_pickup else STOP_TIMES_STOP_TYPE_COORDINATE_DRIVER, 
                STOP_TIMES_TIMEPOINT_APPROXIMATE) 
            for seq_nr, stop in enumerate(carpool.stops)]
        return stop_times

    def _path_for_ride(self, carpool):
        points = self._stop_coords(carpool.stops)
        return self.router.path_for_stops(points)
    
    def _stop_coords(self, stops):
        # Retrieve coordinates of all officially announced stops (start, intermediate, target)
        return [Point(stop.lon, stop.lat) for stop in stops]

    def _estimate_times(self, path, distances_from_start):
        cumulated_distance = 0
        cumulated_time = 0
        stop_times = []
        instructions = path["instructions"]

        cnt = 0
        instr_distance = instructions[cnt]["distance"]
        instr_time = instructions[cnt]["time"]

        for distance in distances_from_start:       
            while cnt < len(instructions) and cumulated_distance + instructions[cnt]["distance"] < distance:
                cumulated_distance = cumulated_distance + instructions[cnt]["distance"]
                cumulated_time = cumulated_time + instructions[cnt]["time"]
                cnt = cnt + 1
            
            if cnt < len(instructions):
                if instructions[cnt]["distance"] ==0:
                    raise RoutingException("Origin and destinaction too close")
                percent_dist = (distance - cumulated_distance) / instructions[cnt]["distance"]
                stop_time = cumulated_time + percent_dist * instructions[cnt]["time"]
                stop_times.append(stop_time)
            else:
                logger.debug("distance {} exceeds total length {}, using max arrival time {}".format(distance, cumulated_distance, cumulated_time))
                stop_times.append(cumulated_time)
        return stop_times

    def _stops_and_stop_times(self, start_time, trip_id, stops_frame):
        # Assumptions: 
        # arrival_time = departure_time
        # pickup_type, drop_off_type for origin: = coordinate/none
        # pickup_type, drop_off_type for destination: = none/coordinate
        # timepoint = approximate for origin and destination (not sure what consequences this might have for trip planners)
        number_of_stops = len(stops_frame.index)
        total_distance = stops_frame.iloc[number_of_stops-1]["distance"]
        
        first_stop_time = GtfsTimeDelta(hours = start_time.hour, minutes = start_time.minute, seconds = start_time.second) 
        stop_times = []
        seq_nr = 0
        for i in range(0, number_of_stops):
            current_stop = stops_frame.iloc[i]

            if not current_stop.id:
                continue
            elif i == 0:
                if (stops_frame.iloc[1].time-current_stop.time) < 1000:
                    # skip custom stop if there is an official stop very close by
                    logger.debug("Skipped stop %s", current_stop.id)
                    continue
            else:
               if (current_stop.time-stops_frame.iloc[i-1].time) < 5000 and not i==1 and not is_carpooling_stop(current_stop.id, current_stop.stop_name) and not stops_frame.iloc[i-1].id is None:
                    # skip latter stop if it's very close (<5 seconds drive) by the preceding
                    logger.debug("Skipped stop %s", current_stop.id)
                    continue
            trip_time = timedelta(milliseconds=int(current_stop.time))
            is_dropoff = self._is_dropoff_stop(current_stop, total_distance)
            is_pickup = self._is_pickup_stop(current_stop, total_distance)
            # TODO would be nice if possible to publish a minimum shared distance 
            pickup_type = STOP_TIMES_STOP_TYPE_COORDINATE_DRIVER if is_pickup else STOP_TIMES_STOP_TYPE_NONE
            dropoff_type = STOP_TIMES_STOP_TYPE_COORDINATE_DRIVER if is_dropoff else STOP_TIMES_STOP_TYPE_NONE
            
            if is_pickup and not is_dropoff:
                pickup_dropoff = PickupDropoffType.only_pickup
            elif not is_pickup and is_dropoff:
                pickup_dropoff = PickupDropoffType.only_dropoff
            else:
                pickup_dropoff = PickupDropoffType.pickup_and_dropoff

            next_stop_time = first_stop_time + trip_time
            seq_nr += 1
            stop_times.append(StopTime(**{
                'arrivalTime': str(next_stop_time), 
                'departureTime': str(next_stop_time), 
                'id': current_stop.id, 
                'pickup_dropoff': pickup_dropoff,
                'name': str(current_stop.stop_name),
                'lat': current_stop.y,
                'lon': current_stop.x
                }))

        return stop_times
    
    def _is_dropoff_stop(self, current_stop, total_distance):
        return current_stop["distance"] >= 0.5 * total_distance
        
    def _is_pickup_stop(self, current_stop, total_distance):
        return current_stop["distance"] < 0.5 * total_distance
