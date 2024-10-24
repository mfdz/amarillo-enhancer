# separate file so that it can be imported without initializing FastAPI
from amarillo.utils.container import container
import json
import logging

from amarillo_stops import stops
from .services.trips import TripTransformer
from amarillo.services.agencies import AgencyService
from amarillo.services.regions import RegionService

logger = logging.getLogger(__name__)

def configure_services():
    container['agencies'] = AgencyService()
    logger.info("Loaded %d agencies", len(container['agencies'].agencies))
    
    container['regions'] = RegionService()
    logger.info("Loaded %d regions", len(container['regions'].regions))

def configure_enhancer_services():
    global transformer
    configure_services()

    logger.info("Load stops...")
    with open('data/stop_sources.json') as stop_sources_file:
        stop_sources = json.load(stop_sources_file)
        stop_store = stops.StopsStore(stop_sources)
    
    stop_store.load_stop_sources()
    # TODO: do we need container?
    container['stops_store'] = stop_store

    transformer = TripTransformer(stop_store)
