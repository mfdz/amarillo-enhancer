# amarillo-enhancer

Enhancing Amarillo carpools as standalone (Docker) service.

This service complements the Amarillo service, taking Amarillo carpool files and filling in route information with additional stops and stop time data. 

# Usage

## 1. Configuration

### Create `data/stop_sources.json`

Example contents:
```json
[
    {"url": "https://datahub.bbnavi.de/export/rideshare_points.geojson", "vicinity": 50},
    {"url": "https://data.mfdz.de/mfdz/stops/stops_zhv.csv", "vicinity": 50},
    {"url": "https://data.mfdz.de/mfdz/stops/parkings_osm.csv", "vicinity": 500}
]
```

You can configure the stop sources file location with the environment variable `stop_sources_file`.

<!-- 
-- seems like regions are not used, maybe we can remove them 
### Add region files `data/region`

File name should be `{region_id}.json`

Example (`by.json`):
```json
{"id": "by", "bbox": [ 8.97, 47.28, 13.86, 50.56]}
``` -->


### Uvicorn configuration

`amarillo-enhancer` uses `uvicorn` to run. Uvicorn can be configured as normal by passing in arguments such as `--port 8001` to change the port number.

### Graphhopper

`amarillo-enhancer` uses a Graphhopper service for routing. You can configure the service that is used with the environment variable `graphhopper_base_url`. By default it is `https://api.mfdz.de/gh'`

## 2. Make requests to the enhancer

To enhance a trip, make a POST request to  `/` with the carpool data as the body. The enhancer will respond with the same carpool object enhanced with additional stop time and path data. The enhancer does not save the generated file.

## 3. Configure the enhancer URL for Amarillo

When Amarillo receives a new carpool object, after returning an OK response it will make a request to the enhancer configured through the environment variable `enhancer_url`. By default it points to `'http://localhost:8001'`.

# Run with uvicorn

- Python 3.10 with pip
- python3-venv

Create a virtual environment `python3 -m venv venv`.

Activate the environment and install the dependencies `pip install -r requirements.txt`.

Run `uvicorn amarillo-enhancer.enhancer:app`. 

In development, you can use `--reload`. 

# Run with docker
You can download a container image from the [MFDZ package registry](https://github.com/orgs/mfdz/packages?repo_name=amarillo-gtfs-generator).

Example command:
```bash
docker run -it --rm --name amarillo-gtfs-generator -p 8002:80 -e TZ=Europe/Berlin -v $(pwd)/data:/app/data amarillo-gtfs-generator```