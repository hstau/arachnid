''' Mask a volume

This |spi| batch file (`spi-mask`) generates a masked volume. It supports:
    
    #. Smoothed spherical masks
    #. Adaptive tight masks
    #. Existing masks in a file

Tips
====

 #. A good value for the density threshold can be found manually in Chimera
 #. The size of a spherical mask is the `pixel-diameter` from the SPIDER params file
 #. The `mask-edge-width` also increases the size of the mask by the given number of pixels
 #. Setting `--volume-mask` to N in this script is an error
 

Examples
========

.. sourcecode :: sh
    
    # Adaptively tight mask a volume
    
    $ spi-mask vol01.spi -o masked_vol01.spi --volume-mask A
    
    # Mask a volume with a cosine smoothed spherical mask
    
    $ spi-mask vol01.spi -o masked_vol01.spi --volume-mask C --mask-edge-width 10
    
    # Mask a volume with a mask in a file
    
    $ spi-mask vol01.spi -o masked_vol01.spi --volume-mask mask_file.spi

Critical Options
================

.. program:: spi-mask

.. option:: -i <FILENAME1,FILENAME2>, --input-files <FILENAME1,FILENAME2>, FILENAME1 FILENAME2
    
    List of input filenames containing volumes.
    If you use the parameters `-i` or `--inputfiles` they must be comma separated 
    (no spaces). If you do not use a flag, then separate by spaces. For a 
    very large number of files (>5000) use `-i "filename*"`
    
.. option:: -o <FILENAME>, --output <FILENAME>
    
    Output filename for masked volume with correct number of digits (e.g. masked_0000.spi)

..option:: volume-mask <('A', 'C', 'G' or FILENAME)>
    
    Set the type of mask: C for cosine and G for Gaussian and N for no mask and A for adaptive tight mask or a filepath for external mask

.. option:: -p <FILENAME>, --param-file <FILENAME> 
    
    Path to SPIDER params file

.. option:: --bin-factor <FLOAT>
    
    Number of times to decimate params file

Spherical Mask Options
=======================

..option:: --mask-edge-width <INT>

    Set edge with of the mask (for Gaussian this is the half-width)

Adaptive Tight Mask Options
===========================

..option:: --threshold <STR or FLOAT>

    Threshold for density or 'A' for auto threshold
    
..option:: --ndilate <INT>

    Number of times to dilate the mask

..option:: --gk-size <INT>
 
     Size of the real space Gaussian kernel (must be odd!)

..option:: --gk-sigma <FLOAT>

    Width of the real space Gaussian kernel

Other Options
=============

This is not a complete list of options available to this script, for additional options see:

    #. :ref:`Options shared by all scripts ... <shared-options>`
    #. :ref:`Options shared by |spi| scripts... <spider-options>`
    #. :ref:`Options shared by file processor scripts... <file-proc-options>`
    #. :ref:`Options shared by SPIDER params scripts... <param-options>`


.. Created on Aug 12, 2012
.. codeauthor:: Robert Langlois <rl2528@columbia.edu>
'''

from ..core.metadata import spider_params, spider_utility, format_utility
from ..core.image import ndimage_utility, ndimage_file
from ..core.spider import spider
import logging

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

def process(filename, output, **extra):
    ''' Create a reference from from a given density map
    
    :Parameters:
    
    filename : str
               Input volume file
    output : str
             Output reference file
    extra : dict
            Unused key word arguments
             
    :Returns:
    
    filename : str
               Filename for correct location
    '''
    
    if spider_utility.is_spider_filename(filename):
        output = spider_utility.spider_filename(output, filename)
    mask_volume(filename, output, **extra)
    return filename

def mask_volume(filename, outputfile, spi, volume_mask='N', prefix=None, **extra):
    ''' Mask a volume
    
    :Parameters:
    
    filename : str
               Filename of the input volume
    outputfile : str
                 Filename for output masked volume
    spi : spider.Session
          Current SPIDER session
    volume_mask : str, infile
                  Set the type of mask: C for cosine and G for Gaussian and N for no mask and A for adaptive tight mask or a filename for external mask
    prefix : str
             Prefix for the mask output file
    extra : dict
            Unused keyword arguments
    
    :Returns:
    
    outputfile : str
                 Filename for masked volume
    '''
    
    if prefix is not None: format_utility.add_prefix(outputfile, prefix)
    volume_mask = volume_mask.upper()
    if volume_mask == 'A':
        tightmask(spider.nonspi_file(spi, filename, outputfile), spi.replace_ext(outputfile), **extra)
    elif volume_mask in ('C', 'G'):
        spherical_mask(filename, outputfile, spi, volume_mask, **extra)
    elif volume_mask == 'N':
        if outputfile != filename: spi.cp(filename, outputfile)
    elif volume_mask != "":
        apply_mask(spider.nonspi_file(spi, filename, outputfile), spi.replace_ext(outputfile), spi.replace_ext(volume_mask))
    else: return filename
    return outputfile

def spherical_mask(filename, outputfile, spi, volume_mask, mask_edge_width=10, pixel_diameter=None, **extra):
    ''' Create a masked volume with a spherical mask
    
    :Parameters:
    
    filename : str
               Filename of the input volume
    outputfile : str
                 Filename for output masked volume
    spi : spider.Session
          Current SPIDER session
    volume_mask : str
                  Set the type of mask: C for cosine and G for Gaussian smoothed spherical mask
    mask_edge_width : int
                      Set edge with of the mask (for Gaussian this is the half-width)
    pixel_diameter : int
                     Diameter of the object in pixels
    extra : dict
            Unused keyword arguments
    
    :Returns:
    
    outputfile : str
                 Filename for masked volume
    '''
    
    if pixel_diameter is None: raise ValueError, "pixel_diameter must be set"
    width = spider.image_size(spi, filename)[0]/2+1
    radius = pixel_diameter/2+mask_edge_width/2 if volume_mask == 'C' else pixel_diameter/2+mask_edge_width
    return spi.ma(filename, radius, (width, width, width), volume_mask, 'C', mask_edge_width, outputfile=outputfile)

def tightmask(filename, outputfile, threshold, ndilate=1, gk_size=3, gk_sigma=3.0, **extra):
    ''' Tight mask the input volume and write to outputfile
    
    :Parameters:
    
    filename : str
               Input volume
    outputfile : str
                 Output tight masked volume
    threshold : str
                Threshold for density or 'A' for auto threshold
    ndilate : int
              Number of times to dilate the mask
    gk_size : int
              Size of the real space Gaussian kernel (must be odd!)
    gk_sigma : float
               Width of the real space Gaussian kernel
    extra : dict
            Unused keyword arguments
    
    :Returns:
    
    outputfile : str
                 Output tight masked volume
    '''
    
    img = ndimage_file.read_image(filename)
    try: threshold=float(threshold)
    except: threshold=None
    mask = ndimage_utility.tight_mask(img, threshold, ndilate, gk_size, gk_sigma)
    ndimage_file.write_image(outputfile, img*mask)
    return outputfile

def apply_mask(filename, outputfile, maskfile):
    ''' Tight mask the input volume and write to outputfile
    
    :Parameters:
    
    filename : str
               Input volume
    outputfile : str
                 Output tight masked volume
    maskfile : str
               Input file containing the mask
    
    :Returns:
    
    outputfile : str
                 Output tight masked volume
    '''
    
    img = ndimage_file.read_image(filename)
    mask = ndimage_file.read_image(maskfile)
    ndimage_file.write_image(outputfile, img*mask)
    return outputfile

def initialize(files, param):
    # Initialize global parameters for the script
    
    param['spi'] = spider.open_session(files, **param)
    spider_params.read_spider_parameters_to_dict(param['spi'].replace_ext(param['param_file']), param)

def finalize(files, **extra):
    # Finalize global parameters for the script
    _logger.info("Completed")

def setup_options(parser, pgroup=None, main_option=False):
    #Setup options for automatic option parsing
    from ..core.app.settings import setup_options_from_doc
    
    if main_option:
        parser.add_option("-i", input_files=[], help="List of input filenames containing volumes", required_file=True, gui=dict(filetype="file-list"))
        parser.add_option("-o", output="",      help="Output filename for masked volume with correct number of digits (e.g. masked_0000.spi)", gui=dict(filetype="save"), required_file=True)
        spider_params.setup_options(parser, pgroup, True)
    setup_options_from_doc(parser, mask_volume, spherical_mask, tightmask)
    if main_option:
        setup_options_from_doc(parser, spider.open_session)
        parser.change_default(thread_count=4, log_level=3)

def check_options(options, main_option=False):
    #Check if the option values are valid
    from ..core.app.settings import OptionValueError
    
    if main_option:
        spider_params.check_options(options)
        if options.volume_mask == 'N':
            raise OptionValueError, "Invalid parameter: --volume-mask should not be set to 'N', this means no masking"
        if options.volume_mask == "":
            raise OptionValueError, "Invalid parameter: ---volume-mask is empty"
        if not spider_utility.test_valid_spider_input(options.input_files):
            raise OptionValueError, "Multiple input files must have numeric suffix, e.g. vol0001.spi"

def main():
    #Main entry point for this script
    from ..core.app.program import run_hybrid_program
    
    run_hybrid_program(__name__,
        description = '''Mask a volume
                        
                        http://
                        
                        $ %prog vol1.spi vol2.spi -o masked_vol_0001.spi --volume-mask G
                        
                        Uncomment (but leave a space before) the following lines to run current configuration file on
                        
                        source /guam.raid.cluster.software/arachnid/arachnid.rc
                        nohup %prog -c $PWD/$0 > `basename $0 cfg`log &
                        exit 0
                      ''',
        supports_MPI=False,
        use_version = False,
        max_filename_len = 78,
    )
if __name__ == "__main__": main()

