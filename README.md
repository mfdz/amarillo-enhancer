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

## 2. Configure the enhancer URL for Amarillo

When Amarillo receives a new carpool object, after returning an OK response it will make a request to the enhancer configured through the environment variable `enhancer_url`. By default it points to `'http://localhost:8001'`.

### Graphhopper

`amarillo-enhancer` uses a Graphhopper service for routing. You can configure the service that is used with the environment variable `graphhopper_base_url`. By default it is `https://api.mfdz.de/gh'`

# Running in development

- Python 3.10 with pip
- python3-venv

Create a virtual environment:
`python3 -m venv venv`.

Activate the environment:
`. venv/bin/activate`

Install the dependencies: `pip install -r requirements.txt`.

Run with `uvicorn amarillo-enhancer.enhancer:app`. 

In development, you can use `--reload`. Uvicorn can be configured as normal by passing in arguments such as `--port 8001` to change the port number.

# Running with docker

For running a production instance of Amarillo and Amarillo-enhancer together, use [amarillo-compose](https://github.com/mfdz/amarillo-compose).

Otherwise, you can build and run a local version in docker:
```bash
docker build -t amarillo-enhancer .
docker run -it --rm --name amarillo-enhancer -p 8001:80 -e TZ=Europe/Berlin -v $(pwd)/data:/app/data amarillo-enhancer```
```



## Making requests to the enhancer

To enhance a trip, make a POST request to  `/` with the carpool data as the body. The enhancer will respond with the same carpool object enhanced with additional stop time and path data. The enhancer does not save the generated file.

Example:

```bash

curl -X 'POST' \
  'http://localhost:8001/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "id": "1234",
  "agency": "mfdz",
  "deeplink": "http://mfdz.de",
  "stops": [
    {
      "name": "Stuttgart",
      "lat": 48.775845,
      "lon": 9.182932
    },
    {
      "name": "Mannheim",
      "lat": 49.487457,
      "lon": 8.466040
    }
  ],
  "departureTime": "12:34",
  "departureDate": "2025-01-30",
  "lastUpdated": "2025-01-23T12:34:00+00:00"
}'

```

Should return a response with additional stops, stop times and coordinates in the carpool data:

```jsonc

{
    "id": "1234",
    "agency": "mfdz",
    "deeplink": "http://mfdz.de/",
    "stops": [
        {
            "id": "de:08111:6075",
            "name": "Stuttgart, Charlottenplatz",
            "departureTime": "12:34:00",
            "arrivalTime": "12:34:00",
            "lat": 48.776276,
            "lon": 9.182911,
            "pickup_dropoff": "only_pickup"
        },
        {
            "id": "de:08111:6023",
            "name": "Stuttgart, Dorotheenstraße",
            "departureTime": "12:34:09",
            "arrivalTime": "12:34:09",
            "lat": 48.775234,
            "lon": 9.181959,
            "pickup_dropoff": "only_pickup"
        },
        // ... other stops
        {
            "id": "de:08222:2395",
            "name": "Mannheim, Am Friedrichsplatz",
            "departureTime": "13:54:51",
            "arrivalTime": "13:54:51",
            "lat": 49.482642,
            "lon": 8.479252,
            "pickup_dropoff": "only_dropoff"
        },
        {
            "id": "de:08222:2459",
            "name": "Mannheim, Rosengarten",
            "departureTime": "13:55:30",
            "arrivalTime": "13:55:30",
            "lat": 49.485449,
            "lon": 8.475398,
            "pickup_dropoff": "only_dropoff"
        }
    ],
    "departureTime": "12:34:00",
    "departureDate": "2025-01-30",
    "path": {
        "type": "LineString",
        "coordinates": [
            [
                9.182941,
                48.776261
            ],
            [
                9.182474,
                48.775559
            ],
            // ... more coordinates
            [
                8.465909,
                49.488711
            ],
            [
                8.465364,
                49.488122
            ]
        ]
    },
    "lastUpdated": "2025-01-23T12:34:00Z"
}

```
