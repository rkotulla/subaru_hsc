#!/usr/bin/env python

import numpy
import os
import sys
import pyfits

from config import *
sys.path.append(qr_dir)

import podi_logging
import logging


def collect_ccds(filelist, out_filename):
    # print "--", "\n-- ".join(framelist[expid])

    primhdu = pyfits.PrimaryHDU()
    ccdlist = [primhdu]

    for fn in filelist:
        hdulist = pyfits.open(fn)

        #
        # Apply overscan subtraction
        #

        #
        # Merge all single OTAs into a single, large MEF
        #
        ccdlist.append(
            pyfits.ImageHDU(
                data=hdulist[0].data,
                header=hdulist[0].header,
                name="CCD.%03d" % (hdulist[0].header['DET-ID'])
            )
        )
        sys.stdout.write(".")
        sys.stdout.flush()

    #
    # All work done, write to file
    #
    out_hdulist = pyfits.HDUList(ccdlist)
    if (out_filename is not None):
        out_hdulist.writeto(out_filename, clobber=True)

    return out_hdulist


if __name__ == "__main__":

    framelist = {}

    logsetup = podi_logging.setup_logging()
    logger = logging.getLogger("SubaruHSC")

    for fn in sys.argv[1:]:
        hdulist = pyfits.open(fn)

        expid = hdulist[0].header['EXP-ID']

        if (not expid in framelist):
            framelist[expid] = []
        
        framelist[expid].append(fn)
        hdulist.close()
        sys.stdout.write(".")
        sys.stdout.flush()



    for expid in framelist:
        logger.info("Working on exposure %s" % (expid))

        out_filename = "%s_comb.fits" % (expid)
        collect_ccds(framelist[expid], out_filename=out_filename)

    podi_logging.shutdown_logging(logsetup)