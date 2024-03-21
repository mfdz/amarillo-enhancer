# separate file so that it can be imported without initializing FastAPI
from amarillo.utils.container import container
import json
import logging
from glob import glob

from amarillo.models.Carpool import Carpool
from amarillo.plugins.enhancer.services import stops
from amarillo.plugins.enhancer.services import trips
from amarillo.plugins.enhancer.services.carpools import CarpoolService
from amarillo.plugins.enhancer.services import gtfs_generator
from amarillo.services.config import config
from amarillo.configuration import configure_services

logger = logging.getLogger(__name__)

enhancer_configured = False

def configure_enhancer_services():
    #Make sure configuration only happens once
    global enhancer_configured 
    if enhancer_configured:
        logger.info("Enhancer is already configured")
        return

    configure_services()

    logger.info("Load stops...")
    with open(config.stop_sources_file) as stop_sources_file:
        stop_sources = json.load(stop_sources_file)
        stop_store = stops.StopsStore(stop_sources)
    
    stop_store.load_stop_sources()
    container['stops_store'] = stop_store
    container['trips_store'] = trips.TripStore(stop_store)
    container['carpools'] = CarpoolService(container['trips_store'])

    logger.info("Restore carpools...")

    for agency_id in container['agencies'].agencies:
        for carpool_file_name in glob(f'data/carpool/{agency_id}/*.json'):
            try:
                with open(carpool_file_name) as carpool_file:
                    carpool = Carpool(**(json.load(carpool_file)))
                    container['carpools'].put(carpool.agency, carpool.id, carpool)
            except Exception as e:
                logger.warning("Issue during restore of carpool %s: %s", carpool_file_name, repr(e))
                    
        # notify carpool about carpools in trash, as delete notifications must be sent
        for carpool_file_name in glob(f'data/trash/{agency_id}/*.json'):
            with open(carpool_file_name) as carpool_file:
                carpool = Carpool(**(json.load(carpool_file)))
                container['carpools'].delete(carpool.agency, carpool.id)

    logger.info("Restored carpools: %s", container['carpools'].get_all_ids())

    enhancer_configured = True
