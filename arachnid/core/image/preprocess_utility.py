''' Set of utilities to preprocess images


.. Created on Nov 14, 2013
.. codeauthor:: robertlanglois
'''
import rotate, ctf, ndimage_utility, ndimage_interpolate

def phaseflip_align2d(img, param, **extra):
    ''' CTF-correct and align images in 2D
    
    :Parameters:
    
    img : array
          2D array of image data
    param : array
            Alignment parameters
    extra : dict
            Unused keyword arguements
    
    :Returns:
    
    img : array
          Aligned and CTF-corrected image
    '''
    
    img = rotate.rotate_image(img, param[3], param[4], param[5])
    ctfimg = ctf.phase_flip_transfer_function(img.shape, param[-1], **extra)
    img = ctf.correct(img, ctfimg)
    return img

def phaseflip_align2d_decimate(img, param, bin_factor, **extra):
    ''' CTF-correct and align images in 2D
    
    :Parameters:
    
    img : array
          2D array of image data
    param : array
            Alignment parameters
    extra : dict
            Unused keyword arguements
    
    :Returns:
    
    img : array
          Aligned and CTF-corrected image
    '''
    
    img = rotate.rotate_image(img, param[3], param[4], param[5])
    ctfimg = ctf.phase_flip_transfer_function(img.shape, param[-1], **extra)
    img = ctf.correct(img, ctfimg).copy()
    img = ndimage_interpolate.downsample(img, bin_factor)
    return img

def phaseflip_shift(img, param, **extra):
    ''' CTF-correct and shift images in 2D
    
    :Parameters:
    
    img : array
          2D array of image data
    param : array
            Alignment parameters
    extra : dict
            Unused keyword arguements
    
    :Returns:
    
    img : array
          Aligned and CTF-corrected image
    '''
    
    img=ndimage_utility.fourier_shift(img, param[4], param[5])
    ctfimg = ctf.phase_flip_transfer_function(img.shape, param[-1], **extra)
    img = ctf.correct(img, ctfimg)
    return img

