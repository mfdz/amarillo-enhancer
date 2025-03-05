from .models.Carpool import Carpool
from .services.trips import TripTransformer
from .services.routing import RoutingException
import logging
import logging.config
from fastapi import FastAPI, status, Body, HTTPException
from .configuration import configure_enhancer_services
from amarillo.utils.container import container
from amarillo.utils.utils import carpool_distance_in_m


logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
logger = logging.getLogger("enhancer")

#TODO: clean up metadata
app = FastAPI(title="Amarillo Enhancer",
              description="This service allows carpool agencies to publish "
                          "their trip offers, so routing services may suggest "
                          "them as trip options. For carpool offers, only the "
                          "minimum required information (origin/destination, "
                          "optionally intermediate stops, departure time and a "
                          "deep link for booking/contacting the driver) needs to "
                          "be published, booking/contact exchange is to be "
                          "handled by the publishing agency.",
              version="0.0.1",
              # TODO 404
              terms_of_service="http://mfdz.de/carpool-hub-terms/",
              contact={
                  # "name": "unused",
                  # "url": "http://unused",
                  "email": "info@mfdz.de",
              },
              license_info={
                  "name": "AGPL-3.0 License",
                  "url": "https://www.gnu.org/licenses/agpl-3.0.de.html",
              },
              openapi_tags=[
                  {
                      "name": "carpool",
                      # "description": "Find out more about Amarillo - the carpooling intermediary",
                      "externalDocs": {
                          "description": "Find out more about Amarillo - the carpooling intermediary",
                          "url": "https://github.com/mfdz/amarillo",
                      },
                  }],
              redoc_url=None
              )
configure_enhancer_services()
stops_store = container['stops_store']
transformer : TripTransformer = TripTransformer(stops_store)
# logger.info(transformer)

@app.post("/",
             operation_id="enhancecarpool",
             summary="Add a new or update existing carpool",
             description="Carpool object to be enhanced",
             response_model=Carpool, # TODO
             response_model_exclude_none=True,
             responses={
                 status.HTTP_404_NOT_FOUND: {
                     "description": "Agency does not exist"},
                 
                })
#TODO: add examples
async def post_carpool(carpool: Carpool = Body(...)) -> Carpool:

    if len(carpool.stops) < 2 or carpool_distance_in_m(carpool) < 1000:
        raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Failed to add carpool {carpool.agency}:{carpool.id}: distance too low")

    logger.info(f"POST trip {carpool.agency}:{carpool.id}.")
    try:
        enhanced_carpool = transformer.enhance_carpool(carpool)

        if len(enhanced_carpool.stops) < 2:
            raise HTTPException(
                status_code=status.HTTP_424_FAILED_DEPENDENCY,
                detail="Failed to add carpool %s: less than two stops after enhancement")

    except RoutingException as err:
        raise HTTPException(
        status_code=status.HTTP_424_FAILED_DEPENDENCY,
        detail=repr(err),
    )

    return enhanced_carpool