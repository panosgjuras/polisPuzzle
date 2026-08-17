import pandas as pd

# Copy this function to Module 1: diary_prep

def pool_pid(socio):
    
    """
    
    It updates the pid index, it is now pid + city
    
    City indicates the survey where the data came from
    
    It is an identifier that is used only in the pool.
    
    """
    
    socio = socio.copy()

    socio.index = (
        socio.index.astype(str)
        + "_"
        + socio["city"].astype(str)
    )
    socio.index.name = "pid"

    socio = socio.drop(columns=["city"])

    return socio

def write_socio_to_pool(pool, socio):
    
    """
    This writes the new socio file to the existing pool.
    """
    
    new_socio = pool_pid(socio)

    pool = pd.concat(
        [pool, new_socio],
        axis=0
    )
    
    pool = pool[~pool.index.duplicated(keep="last")] # Do not add again the same data in the pool
    pool.index.name = "pid"

    return pool
