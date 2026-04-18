import sys, random
from . import datapoint, database, web_api

def main():

    print("Setting up DB")
    db = database.Database(
        token=sys.argv[1]
    )
    print("DB Done!")
    
    print("Spinning up web API")
    api = web_api.WebAPI(
        host="0.0.0.0",
        port=8099,
        database=db
    )

    api.start()
    