import sys, random
from . import datapoint, database, web_api

def main():
    #conf = datapoint.Confidence(2.2, 0.92)
    #print(conf.str_representation())
    #k = datapoint.Datapoint("Moisture", 55.02, conf, "%")
    #print(f'{k.parameter} reading: {k.value}±{k.confidence.interval}{k.units} with {k.confidence.level}% confidence')
    #print("Aaaaaand we are OFF!! :D")
    #print(sys.argv[0])
    #print()
    #print()

    #unit = "THEMOON"

    print("Setting up DB")
    db = database.Database(
        token=sys.argv[1]
    )
    print("DB Done!")

    #print("Spawning client")
    #client = db.spawn_client()
    #print("client Done!")

    #for x in range (2):
    #    print("----------------------------------------------")
    #    print(f'Measurement {x}')
    #    value = random.random() * 100
    #    k = datapoint.Datapoint("Moisture", value, conf, "%")
    #    print("writing measurement to DB")
    #    client.write_measurement(unit, k)
    #    print("writing done!")
    #    print()
    #    print("Reading all from db")
    #    df = client.read_all(unit, "Moisture")

    #    print(df)
    
    print("Spinning up web API")
    api = web_api.WebAPI(
        host="0.0.0.0",
        port=8099,
        database=db
    )

    api.start()
    