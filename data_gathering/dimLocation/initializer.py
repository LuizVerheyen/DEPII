import os
import pandas as pd

from data_gathering.hulp_functies import filterNewRows

def dimLocation():
    """Laad DimLocation vanuit Excel en clean."""
    cwd = os.getcwd()
    data_dir = os.path.join(cwd, "data")
    if not os.path.exists(data_dir):
        data_dir = os.path.abspath(os.path.join(cwd, "..", "..", "data"))
    zipcodes = pd.read_excel(os.path.join(data_dir, "zipcodes_num_nl_2025.xls"))
    dimLocation = zipcodes.drop(columns=["Deelgemeente"], errors="ignore")
    dimLocation.rename(columns={
        "Postcode": "PostalCode",
        "Plaatsnaam": "Municipality",
        "Hoofdgemeente": "MainMunicipality",
        "Provincie": "Province"
    }, inplace=True)
    for col in dimLocation.columns[1:]:
        dimLocation[col] = dimLocation[col].astype(str).str.title()

    dimLocation = filterNewRows(dimLocation, 'DimLocation', ["PostalCode", "Municipality", "MainMunicipality", "Province"])
    
    return dimLocation