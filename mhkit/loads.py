from scipy.stats import binned_statistic
import matplotlib.pyplot as plt 
import pandas as pd 
import numpy as np
import fatpack

###### General functions

def bin_statistics(data,bin_against,bin_edges,data_signal=[]):
    """
    Bins calculated statistics against data signal (or channel) 
    according to IEC TS 62600-3:2020 ED1.
    
    Parameters:
    -----------
    data : pandas DataFrame
       Time-series statistics of data signal(s)
    
    bin_against : array
        Data signal to bin data against (e.g. wind speed)
    
    bin_edges : array
        Bin edges with consistent step size

    data_signal : list, optional 
        List of data signal(s) to bin, default = all data signals
    
    Returns:
    --------
    bin_mean : pandas DataFrame
        Mean of each bin

    bin_std : pandas DataFrame
        Standard deviation of each bim
    """

    try: bin_against = np.asarray(bin_against) 
    except: pass
    try: bin_edges = np.asarray(bin_edges)
    except: pass
    
    assert isinstance(data, pd.DataFrame), 'data must be of type pd.DataFram'
    assert isinstance(bin_against, np.ndarray), 'bin_against must be of type np.ndarray'
    assert isinstance(bin_edges, np.ndarray), 'bin_edges must be of type np.ndarray'

    # Determine variables to analyze
    if len(data_signal)==0: # if not specified, bin all variables
        data_signal=data.columns.values
    else:
        assert isinstance(data_signal, list), 'must be of type list'

    # Pre-allocate list variables
    bin_stat_list = []
    bin_std_list = []

    # loop through data_signal and get binned means
    for signal_name in data_signal:
        # Bin data
        bin_stat = binned_statistic(bin_against,data[signal_name],statistic='mean',bins=bin_edges)
        # Calculate std of bins
        std = []
        stdev = pd.DataFrame(data[signal_name])
        stdev.set_index(bin_stat.binnumber,inplace=True)
        for i in range(1,len(bin_stat.bin_edges)):
            try:
                temp = stdev.loc[i].std(ddof=0)
                std.append(temp[0])
            except:
                std.append(np.nan)
        bin_stat_list.append(bin_stat.statistic)
        bin_std_list.append(std)
 
    # Convert to DataFrames
    bin_mean = pd.DataFrame(np.transpose(bin_stat_list),columns=data_signal)
    bin_std = pd.DataFrame(np.transpose(bin_std_list),columns=data_signal)

    # Check for nans 
    if bin_mean.isna().any().any():
        print('Warning: some bins may be empty!')

    return bin_mean, bin_std

def tip_speed_ratio(rotor_speed,rotor_diameter,inflow_speed):
    '''
    Function used to calculate the tip speed ratio (TSR) of a MEC device with rotor

    Parameters:
    -----------
    rotor_speed : numpy array
        Rotor speed [revolutions per second]
    rotor_diameter : float/int
        Diameter of rotor [m]
    inflow_speed : numpy array
        Velocity of inflow condition [m/s]

    Returns:
    --------
    TSR : numpy array
        Calculated tip speed ratio (TSR)
    '''
    
    try:
        rotor_speed = np.asarray(rotor_speed)
        inflow_speed = np.asarray(inflow_speed)
    except:
        pass
    assert isinstance(rotor_speed, np.ndarray), 'rotor_speed must be of type np.ndarray'
    assert isinstance(rotor_diameter, (float,int)), 'rotor diameter must be of type int or float'
    assert isinstance(inflow_speed, np.ndarray), 'inflow_speed must be of type np.ndarray'

    # get rotational velocity in m/s
    rotor_velocity = rotor_speed * np.pi*rotor_diameter

    # calculate TSR
    TSR = rotor_velocity / inflow_speed

    return TSR

def power_coefficient(power,inflow_speed,capture_area,rho):
    '''
    Function that calculates the power coefficient of MEC device

    Parameters:
    -----------
    power : numpy array
        Power output signal of device after losses [W]
    inflow_speed : numpy array
        Speed of inflow [m/s]
    capture_area : float/int
        Projected area of rotor normal to inflow [m^2]
    rho : float/int
        Density of environment [kg/m^3]

    Returns:
    --------
    Cp : numpy array
        Power coefficient of device [-]
    '''
    
    try: power = np.asarray(power)
    except:pass
    try: inflow_speed = np.asarray(inflow_speed)
    except:pass
    
    assert isinstance(power, np.ndarray), 'power must be of type np.ndarray'
    assert isinstance(inflow_speed, np.ndarray), 'inflow_speed must be of type np.ndarray'
    assert isinstance(capture_area, (float,int)), 'capture_area must be of type int or float'
    assert isinstance(rho, (float,int)), 'rho must be of type int or float'

    # calculate predicted power from inflow
    power_in = (0.5 * rho * capture_area * inflow_speed**3)

    # calculate Cp ratio
    Cp = power / power_in 

    return Cp

def blade_moments(blade_coefficients,flap_offset,flap_raw,edge_offset,edge_raw):
    '''
    Transfer function for deriving blade flap and edge moments using blade matrix.

    Parameters:
    -----------
    blade_coefficients : numpy array
        Derived blade calibration coefficients listed in order of D1, D2, D3, D4
    flap_offset : float
        Derived offset of raw flap signal obtained during calibration process
    flap_raw : numpy array
        Raw strain signal of blade in the flapwise direction
    edge_offset : float
        Derived offset of raw edge signal obtained during calibration process
    edge_raw : numpy array
        Raw strain signal of blade in the edgewise direction
    
    Returns:
    --------
    M_flap : numpy array
        Blade flapwise moment in SI units
    M_edge : numpy array
        Blade edgewise moment in SI units
    '''
    # check data types
    try:
        blade_coefficients = np.asarray(blade_coefficients)
        flap_raw = np.asarray(flap_raw)
        edge_raw = np.asarray(edge_raw)
    except:
        pass            
    assert isinstance(blade_coefficients, np.ndarray), 'blade_coefficients must be of type np.ndarray'
    assert isinstance(flap_offset, (float,int)), 'flap_offset must be of type int or float'
    assert isinstance(flap_raw, np.ndarray), 'flap_raw must be of type np.ndarray'
    assert isinstance(edge_offset, (float,int)), 'edge_offset must be of type int or float'
    assert isinstance(edge_raw, np.ndarray), 'edge_raw must be of type np.ndarray'

    # remove offset from raw signal
    flap_signal = flap_raw - flap_offset
    edge_signal = edge_raw - edge_offset

    # apply matrix to get load signals
    M_flap = blade_coefficients[0]*flap_signal + blade_coefficients[1]*edge_signal
    M_edge = blade_coefficients[2]*flap_signal + blade_coefficients[3]*edge_signal

    return M_flap, M_edge


################ Fatigue functions

def damage_equivalent_load(data_signal, m, bin_num=100, data_length=600):
    """
    Calculates the damage equivalent load of a single data signal (or channel) 
    based on IEC TS 62600-3:2020 ED1. 4-point rainflow counting algorithm from 
    fatpack module is based on the following resources:
        
    - `C. Amzallag et. al. Standardization of the rainflow counting method for
      fatigue analysis. International Journal of Fatigue, 16 (1994) 287-293`
    - `ISO 12110-2, Metallic materials - Fatigue testing - Variable amplitude
      fatigue testing.`
    - `G. Marsh et. al. Review and application of Rainflow residue processing
      techniques for accurate fatigue damage estimation. International Journal
      of Fatigue, 82 (2016) 757-765`
    
    Parameters:
    -----------
    data_signal : array
        Data signal being analyzed
    
    m : float/int
        Fatigue slope factor of material
    
    bin_num : int
        Number of bins for rainflow counting method (minimum=100)
    
    data_length : float/int
        Length of measured data (seconds)
    
    Returns:
    --------
    DEL : float
        Damage equivalent load of single data signal
    """
    
    try: data_signal = np.array(data_signal)
    except: pass
    
    assert isinstance(data_signal, np.ndarray), 'data_signal must be of type np.ndarray'
    assert isinstance(m, (float,int)), 'm must be of type float or int'
    assert isinstance(bin_num, (float,int)), 'bin_num must be of type float or int'
    assert isinstance(data_length, (float,int)), 'data_length must be of type float or int'

    rainflow_ranges = fatpack.find_rainflow_ranges(data_signal,k=256)

    # Range count and bin
    Nrf, Srf = fatpack.find_range_count(rainflow_ranges, bin_num)

    DELs = Srf**m * Nrf / data_length
    DEL = DELs.sum() ** (1/m)

    return DEL

    
################ plotting functions

def plot_statistics(x,y_mean,y_max,y_min,y_stdev=[],xlabel=None,
                    ylabel=None,title=None,savepath=None):
    """
    Plot showing standard raw statistics of variable

    Parameters:
    -----------
    x : numpy array
        Array of x-axis values
    y_mean : numpy array
        Array of mean statistical values of variable
    y_max : numpy array
        Array of max statistical values of variable
    y_min : numpy array
        Array of min statistical values of variable
    y_stdev : numpy array, optional
        Array of standard deviation statistical values of variable
    xlabel : string, optional
        xlabel for plot
    ylabel : string, optional
        ylabel for plot
    title : string, optional
        Title for plot
    savepath : string, optional
        Path and filename to save figure. Plt.show() is called otherwise

    Returns:
    --------
    ax : matplotlib pyplot axes
    """
    
    try: x = np.array(x)
    except: pass       
    try: y_mean = np.array(y_mean)
    except: pass            
    try:y_max = np.array(y_max)
    except: pass
    try: y_min = np.array(y_min)
    except: pass
    
    assert isinstance(x, np.ndarray), 'x must be of type np.ndarray'
    assert isinstance(y_mean, np.ndarray), 'y_mean must be of type np.ndarray'
    assert isinstance(y_max, np.ndarray), 'y_max must be of type np.ndarray'
    assert isinstance(y_min, np.ndarray), 'y_min must be of type np.ndarray'

    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot(x,y_max,'^',label='max',mfc='none')
    ax.plot(x,y_mean,'o',label='mean',mfc='none')
    ax.plot(x,y_min,'v',label='min',mfc='none')
    if len(y_stdev)>0: ax.plot(x,y_stdev,'+',label='stdev',c='m')
    ax.grid(alpha=0.4)
    ax.legend(loc='best')
    if xlabel!=None: ax.set_xlabel(xlabel)
    if ylabel!=None: ax.set_ylabel(ylabel)
    if title!=None: ax.set_title(title)
    fig.tight_layout()
    if savepath==None: plt.show()
    else: 
        fig.savefig(savepath)
        plt.close()
    return ax

def plot_bin_statistics(bin_centers, bin_mean,bin_max, bin_min,
                        bin_mean_std, bin_max_std, bin_min_std,
                        **kwargs):
    """
    Plot showing standard binned statistics of single variable

    Parameters:
    -----------
    bin_centers : numpy array
        x-axis bin center values
    bin_mean : numpy array
        Binned mean statistical values of variable
    bin_max : numpy array
        Binned max statistical values of variable
    bin_min : numpy array
        Binned min statistical values of variable
     : numpy array
        Standard deviations of mean binned statistics
    bin_max_std : numpy array
        Standard deviations of max binned statistics
    bin_min_std : numpy array
        Standard deviations of min binned statistics
    **kwargs : optional             
        x_label : string
            x axis label for plot
        y_label : string
            y axis label for plot
        title : string, optional
            Title for plot
        save_path : string
            Path and filename to save figure.

    Returns:
    --------
    ax : matplotlib pyplot axes
    """
    
    x_label   = kwargs.get("x_label", None)
    y_label   = kwargs.get("y_label", None)
    title     = kwargs.get("title", None)
    save_path = kwargs.get("save_path", None)
    
    assert isinstance(bin_centers, np.ndarray), ('bin_centers must be '
                                                 'of type np.ndarray')
    assert isinstance(bin_mean, np.ndarray), ('bin_mean must be of '
                                               'type np.ndarray')
    assert isinstance(bin_max, np.ndarray), ('bin_max must be of '
                                             'type np.ndarray')
    assert isinstance(bin_min, np.ndarray), ('bin_min must be of type '
                                                 'type np.ndarray')
    assert isinstance(bin_mean_std, np.ndarray), ('bin_mean_std must be '
                                                  'of type np.ndarray')
    assert isinstance(bin_max_std, np.ndarray), ('bin_max_std must be '
                                                 'of type np.ndarray')    
    assert isinstance(bin_min_std, np.ndarray), ('bin_min_std must be '
                                                 'of type np.ndarray')
    assert isinstance(x_label, str), 'x_label must be of type str'
    assert isinstance(y_label, str), 'y_label must be of type str'
    assert isinstance(title, str), 'title must be of type str'
    assert isinstance(save_path, str), 'save_path must be of type str'
    
    fig, ax = plt.subplots(figsize=(7,5))
    ax.errorbar(bin_centers,bin_max,marker='^',mfc='none',
                yerr=bin_max_std,capsize=4,label='max')
    ax.errorbar(bin_centers,bin_mean,marker='o',mfc='none',
                yerr=bin_mean_std,capsize=4,label='mean')
    ax.errorbar(bin_centers,bin_min,marker='v',mfc='none',
               yerr=bin_min_std,capsize=4,label='min')
    
    ax.grid(alpha=0.5)
    ax.legend(loc='best')
    
    if xlabel!=None: ax.set_xlabel(xlabel)
    if ylabel!=None: ax.set_ylabel(ylabel)
    if title!=None: ax.set_title(title)
    fig.tight_layout()
    if savepath==None: plt.show()
    else: 
        fig.savefig(savepath)
        plt.close()
    return ax
