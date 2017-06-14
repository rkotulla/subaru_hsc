#!/usr/bin/env python

import numpy
import os
import sys
import pyfits

if __name__ == "__main__":

    framelist = {}
    
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
        print expid
        # print "--", "\n-- ".join(framelist[expid])
        
        primhdu = pyfits.PrimaryHDU()
        ccdlist = [primhdu]

        for fn in framelist[expid]:
            hdulist = pyfits.open(fn)
            ccdlist.append(
                pyfits.ImageHDU(
                    data=hdulist[0].data,
                    header=hdulist[0].header,
                    name="CCD.%03d" % (hdulist[0].header['DET-ID'])
                    )
                )
            sys.stdout.write(".")
            sys.stdout.flush()

        outfn = "%s_comb.fits" % (expid)
        pyfits.HDUList(ccdlist).writeto(outfn, clobber=True)
