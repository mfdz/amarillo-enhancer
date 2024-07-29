# separate file so that it can be imported without initializing FastAPI
from amarillo.utils.container import container
import json
import logging

from amarillo_stops import stops
from amarillo.utils.utils import assert_folder_exists
from .services.trips import TripTransformer
from amarillo.services.agencies import AgencyService
from amarillo.services.regions import RegionService

logger = logging.getLogger(__name__)

# enhancer_configured = False

def create_required_directories():
    logger.info("Checking that necessary directories exist")
    # Folder to serve GTFS(-RT) from
    assert_folder_exists('data/gtfs')
    # Temp folder for GTFS generation
    assert_folder_exists('data/tmp')

    for agency_id in container['agencies'].agencies:
        for subdir in ['carpool', 'trash', 'enhanced', 'failed']:
            foldername = f'data/{subdir}/{agency_id}'
            logger.debug("Checking that necessary %s exist", foldername)
            assert_folder_exists(f'data/{subdir}/{agency_id}')


def configure_services():
    container['agencies'] = AgencyService()
    logger.info("Loaded %d agencies", len(container['agencies'].agencies))
    
    container['regions'] = RegionService()
    logger.info("Loaded %d regions", len(container['regions'].regions))

    create_required_directories()

def configure_enhancer_services():
    #Make sure configuration only happens once
    # global enhancer_configured 
    global transformer
    # if enhancer_configured:
    #     logger.info("Enhancer is already configured")
    #     return

    configure_services()




    logger.info("Load stops...")
    with open('data/stop_sources.json') as stop_sources_file:
        stop_sources = json.load(stop_sources_file)
        stop_store = stops.StopsStore(stop_sources)
    
    stop_store.load_stop_sources()
    # TODO: do we need container?
    container['stops_store'] = stop_store
    # container['trips_store'] = trips.TripStore(stop_store)
    # container['carpools'] = CarpoolService(container['trips_store'])

    transformer = TripTransformer(stop_store)

    # logger.info("Restore carpools...")

    # for agency_id in container['agencies'].agencies:
    #     for carpool_file_name in glob(f'data/carpool/{agency_id}/*.json'):
    #         try:
    #             with open(carpool_file_name) as carpool_file:
    #                 carpool = Carpool(**(json.load(carpool_file)))
    #                 container['carpools'].put(carpool.agency, carpool.id, carpool)
    #         except Exception as e:
    #             logger.warning("Issue during restore of carpool %s: %s", carpool_file_name, repr(e))
                    
    #     # notify carpool about carpools in trash, as delete notifications must be sent
    #     for carpool_file_name in glob(f'data/trash/{agency_id}/*.json'):
    #         with open(carpool_file_name) as carpool_file:
    #             carpool = Carpool(**(json.load(carpool_file)))
    #             container['carpools'].delete(carpool.agency, carpool.id)

    # logger.info("Restored carpools: %s", container['carpools'].get_all_ids())

    # enhancer_configured = True
