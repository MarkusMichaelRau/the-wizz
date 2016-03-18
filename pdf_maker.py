#! /usr/bin/python

import _core_utils
import input_flags
import _pdf_maker_utils
import h5py
import numpy as np
import sys

if __name__ == "__main__": 
    
    ### First we parse the command line for arguments as usual. See
    ### input_flags.py for a full list of input arguments. 
    args = input_flags.parse_input_pdf_args()
    
    ### Load the file containing all matched pairs of spectroscopic and
    ### photometric objects.
    print("Loading file...")
    hdf5_pair_file = _core_utils.file_checker_loader(args.input_pair_hdf5_file)
    
    ### This is a temporary solution for the KiDS busy week Feb 15th-19th.
    ### TODO:
    ###     Evenutually want this to be a request for single point PDFs from
    ###     machine learning. Maybe put this in it's own method
    unknown_data = _core_utils.file_checker_loader(args.unknown_sample_file)
    
    ### This is where the heavy lifting happens. We create our PDF maker object
    ### which will hold the pair file for use, calculate the over density per
    ### redshift bin, and also store intermediary results for later use. 
    ### Before we can estimate the PDF, we must mask for the objects we want 
    ### to estimate the redshit of. These objects can be color selected,
    ### photo-z selected, or any other object seletion you would like. The code
    ### line below turns the array of indices in the hdf5 pair file, into a
    ### single density estimate around the target object.
    print("Matching indices...")
    pdf_maker = _pdf_maker_utils.collapse_ids_to_single_estimate(
        hdf5_pair_file[args.pair_scale_name], unknown_data, args)
    
    ### Now we figure out what kind of redshift binning we would like to have.
    ### This will be one of the largest impacts on the signal to noise of the
    ### measurement. Some rules of thumb are:
    ###     The narrower bins are in redshift the better. You are measuring a
    ### correlation, the narrower the bin size in comoving distance the more
    ### correlated things will be and thus increase the amplitude. Aka use
    ### Groth/Pebbles[sic] scaling to your advantage.
    ###     For a spectroscopic sample that is selected for a specific redshift
    ### range with few galaxies outside that range (eg DEEP2), adaptive binning
    ### is recommended. This will keep a equal number spectra per redshift bin.
    ### A good rule is to try to have about 100 spectra per redshift bin for max
    ### signal to noise.
    ###     Linear binning is provided as a curtesy and is not nesassarly
    ### recommended. It will not give the best signal to noise compared to
    ### adaptive and has the same draw backs as adaptive is that the bias could
    ### be changing oddly from bin to bin. It is recommended that the user try
    ### adaptive and comoving spaced bins for the best results. Comoving returns
    ### bins that are of equal comoving distance from the line of sight.
    print("creating bins...")
    if args.z_binning_type == 'linear':
        z_bin_edge_array = _pdf_maker_utils._create_linear_redshift_bin_edges(
            args.z_min, args.z_max, args.z_n_bins)
    elif args.z_binning_type == 'adaptive':
        z_bin_edge_array = _pdf_maker_utils._create_adaptive_redshift_bin_edges(
            args.z_min, args.z_max, args.z_n_bins,
            pdf_maker.target_redshift_array)
    elif args.z_binning_type == 'comoving':
        z_bin_edge_array = _pdf_maker_utils._create_comoving_redshift_bin_edges(
            args.z_min, args.z_max, args.z_n_bins)
    else:
        print("Requested binning name invalid. Valid types are:")
        print("\tlinear: linear binning in redshift")
        print("\tadaptive: constant target objects per redshift bin")
        print("\tcomoving: linear binning in comoving distance")
        print("\tRetunning linear binning...")
        z_bin_edge_array = _pdf_maker_utils._create_linear_redshift_bin_edges(
            args.z_min, args.z_max, args.z_n_bins)
    
    print("Calculating region densities...")
    pdf_maker.compute_region_densities(z_bin_edge_array, args.z_max)
    ### Now that we've "collapsed" the estimate around the target object we need
    ### to bin up the results in redshift and create our final PDF.
    print("Calculating pdf...")
    if args.bootstrap_samples is None:
        pdf_maker.compute_pdf_bootstrap(args.n_bootstrap)
    else:
        bootstrap_region_array = np.loadtxt(args.bootstrap_samples,
                                            dtype = np.int_)
        pdf_maker._compute_pdf_bootstrap(bootstrap_region_array)
    ### Now that we have the results. We just need to write them to file and we
    ### are done.
    print("Writing...")
    pdf_maker.write_pdf_to_ascii(args.output_pdf_file_name)
    
    ### TODO:
    ###    Include bootstrapping and writing of the raw boostrap samples. 
    
    print "Done!"