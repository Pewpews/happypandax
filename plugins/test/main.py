import __hpx__ as hpx
import pprint
import sys

log = hpx.get_logger(__name__)

@hpx.subscribe("InitApplication.init")
def init():
    log.info("init")

def main():
    log.info("hi")

if __name__ == '__main__':
    main()