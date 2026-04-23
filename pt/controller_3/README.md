# InfluxDB
*version* 3.0 or later
*location* can be installe locally or remotely
*Note one RPI5s* The default OS that is build for Rapsberry Pi 5 uses a page-size of 16k. This doesn't work with local installation of InfluxDB3, which assumes a page size of 4k. Make sure to change the page size.
This is done in `/boot/firmware/config.txt` by setting the paramaeter `kernel` to `kernel8.img`: `kernel=kernel8.img`