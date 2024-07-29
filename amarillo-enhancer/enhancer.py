from .models.Carpool import Carpool
from .services.trips import TripTransformer
import logging
import logging.config
from fastapi import FastAPI, status, Body
from .configuration import configure_enhancer_services
from amarillo.utils.container import container

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
              servers=[
                  {
                      "description": "MobiData BW Amarillo service",
                      "url": "https://amarillo.mobidata-bw.de"
                  },
                  {
                      "description": "DABB bbnavi Amarillo service",
                      "url": "https://amarillo.bbnavi.de"
                  },
                  {
                      "description": "Demo server by MFDZ",
                      "url": "https://amarillo.mfdz.de"
                  },
                  {
                      "description": "Dev server for development",
                      "url": "https://amarillo-dev.mfdz.de"
                  },
                  {
                      "description": "Server for Mitanand project",
                      "url": "https://mitanand.mfdz.de"
                  },
                  {
                      "description": "Localhost for development",
                      "url": "http://localhost:8000"
                  }
              ],
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

    logger.info(f"POST trip {carpool.agency}:{carpool.id}.")

    enhanced = transformer.enhance_carpool(carpool)

    return enhanced