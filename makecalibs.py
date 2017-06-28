#!/usr/bin/env python

import numpy
import os
import sys
import pyfits
import scipy.ndimage

from config import *
sys.path.append(qr_dir)

import podi_logging
import podi_imcombine


import logging
import argparse

import hsc_combine


if __name__ == "__main__":

    framelist = {}

    logsetup = podi_logging.setup_logging()
    logger = logging.getLogger("SubaruHSC")

    bias_list = []
    dark_list = []
    flat_list = {}

    parser = argparse.ArgumentParser(
        description='Reduce Subaru-HSC frames.')
    parser.add_argument(
        'files', type=str, nargs='+', #nargs=1,
        metavar='input.fits',
        help='list of input files')
    # parser.add_argument('--bias', dest='bias',
    #                     default=None, help='BIAS filename')
    # parser.add_argument('--dark', dest='dark',
    #                     default=None, help='DARK filename')
    # parser.add_argument('--flat', dest='flat',
    #                     default=None, help='FLAT filename')
    # parser.add_argument('--masksat', dest='mask_saturation', type=float,
    #                     default=None, help='mask all saturated pixels above this limit')
    # parser.add_argument('--output', dest='output',
    #                     default=None, help='output filename')
    args = parser.parse_args()


    for fn in args.files:
        hdulist = pyfits.open(fn)

        expid = hdulist[0].header['EXP-ID']

        if (not expid in framelist):
            framelist[expid] = []

            #
            # Also collect information about bias/dark/flat
            #
            data_type = hdulist[0].header['DATA-TYP']
            filter01 = hdulist[0].header['FILTER01']
            if (data_type == "BIAS"):
                bias_list.append(expid)
            elif (data_type == "DARK"):
                dark_list.append(expid)
            elif (data_type == "DOMEFLAT"):
                if (filter01 not in flat_list):
                    flat_list[filter01] = []
                flat_list[filter01].append(expid)

        framelist[expid].append(fn)
        hdulist.close()
        sys.stdout.write(".")
        sys.stdout.flush()

    print "\n"

    #
    # Now create all bias-frames
    #
    if (not os.path.isdir("tmp")):
        os.mkdir("tmp")

    for expid in bias_list:

        reduced_list = []

        reduced_expid = expid[:-2]+"xx"
        tmp_out = "tmp/bias_%s.fits" % (reduced_expid)
        if (not os.path.isfile(tmp_out)):
            print "Creating BIAS frame (--> %s)" % (tmp_out)
            bias_hdu = hsc_combine.collect_ccds(
                filelist=framelist[expid],
                out_filename=tmp_out,
                bias=None, dark=None, flat=None, mask_saturation=None,
            )
        else:
            print "Re-using existing bias from %s" % (tmp_out)
        reduced_list.append(tmp_out)

    master_bias_fn = "bias.fits"
    if (not os.path.isfile(master_bias_fn)):
        print "Creating %s" % (master_bias_fn)
        master_bias = podi_imcombine.imcombine(
            input_filelist=reduced_list,
            outputfile = master_bias_fn,
            operation="sigmaclipmean",
        )
    else:
        print "Master-bias (%s) already exists" % (master_bias_fn)


    #
    # Create all flat-fields
    #
    for filtername in flat_list:

        for expid in flat_list[filtername]:

            reduced_expid = expid[:-2]+"xx"
            tmp_out = "tmp/nflat_%s.fits" % (reduced_expid)
            if (not os.path.isfile(tmp_out)):
                print "Creating normalized flat-field frame (--> %s)" % (tmp_out)
                flat_hdu = hsc_combine.collect_ccds(
                    filelist=framelist[expid],
                    out_filename=None,
                    bias=master_bias_fn,
                    dark=None, flat=None, mask_saturation=None,
                )

                # compute average level in the central CCD
                mean_flat_levels = []
                for ccd in [50,58,49,57]:
                    extname = "CCD.%03d" % (ccd)
                    if (extname not in flat_hdu):
                        continue
                    mean_level = numpy.nanmean(flat_hdu[extname].data)
                    mean_flat_levels.append(mean_level)
                mean_flat_levels = numpy.array(mean_flat_levels)
                flat_normalization = numpy.mean(mean_flat_levels)
                print mean_flat_levels, "-->", flat_normalization

                # normalize all detectors
                for ext in flat_hdu:
                    if ext.data is not None:
                        ext.data /= flat_normalization

                # save file for later
                flat_hdu.writeto(tmp_out, clobber=True)
            else:
                print "Re-using existing flat from %s" % (tmp_out)
            reduced_list.append(tmp_out)

        #
        # Now compute average flat-field
        #
        master_flat_fn = "flat_%s.fits" % (filtername)
        print "Creating %s" % (master_flat_fn)
        master_flat = podi_imcombine.imcombine(
            input_filelist=reduced_list,
            outputfile = master_flat_fn,
            operation="sigmaclipmean",
        )

    podi_logging.shutdown_logging(logsetup)