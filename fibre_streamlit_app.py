import pandas as pd
from pandas import json_normalize
import geopandas as gpd
import numpy as np
#import fiona
import altair as alt
pd.set_option("display.max_row",2000)
pd.set_option("display.max_column",500)
#from IPython.core.interactiveshell import InteractiveShell
#InteractiveShell.ast_node_interactivity = "all"
import warnings
warnings.filterwarnings('ignore')
alt.data_transformers.disable_max_rows()
import numpy as np  
#from scipy.spatial.distance import cdist
from shapely.geometry import Point
from streamlit_folium import folium_static
import folium
from folium import plugins
import branca.colormap as cm
#from folium.plugins import MarkerCluster
from zipfile import ZipFile
from shapely.geometry import LineString
import googlemaps 
import time
import geopy.distance
from scipy.spatial import cKDTree
from io import BytesIO
import streamlit as st
from PIL import Image
from st_aggrid import AgGrid
from glob import glob



width = 1200
height = 500
icon = Image.open('DB.ico')
image = Image.open('DB Logo.png')

st.set_page_config(page_title="Distancias a Nodos de Conectividad",
                    page_icon=icon,
                    layout='wide')
st.image(image)


def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    format1 = workbook.add_format({'num_format': '0.00'}) 
    worksheet.set_column('A:A', None, format1)  
    writer.save()
    processed_data = output.getvalue()
    return processed_data


def ckdnearest(gdA, gdB):

    nA = np.array(list(gdA.geometry.apply(lambda x: (x.x, x.y))))
    nB = np.array(list(gdB.geometry.apply(lambda x: (x.x, x.y))))
    btree = cKDTree(nB)
    dist, idx = btree.query(nA, k=1)
    gdB_nearest = gdB.iloc[idx].drop(columns="geometry").reset_index(drop=True)
    gdf = pd.concat(
        [
            gdA.reset_index(drop=True),
            gdB_nearest,
            pd.Series(dist, name='dist')
        ], 
        axis=1)

    return gdf


def read_geojsons():
    files_fttb = sorted(glob('data/geojson_fttb/*.geojson'))
    fttb_geojsons = pd.concat(gpd.read_file(file) for file in files_fttb)
    files_fibre = sorted(glob('data/geojson_existing_fibre/*.geojson'))
    fttb_fibregeojsons = pd.concat(gpd.read_file(file) for file in files_fibre)
    files_fttb_2 = sorted(glob('data/geojson_FTTB_Project_v04/*.geojson'))
    fttb_fibregeojsons_2 = pd.concat(gpd.read_file(file) for file in files_fttb_2)
    
    return fttb_fibregeojsons,fttb_geojsons,fttb_fibregeojsons_2


@st.cache_data
def linestring_fibre():
    fibre = pd.read_excel('data/ruta_de_fibra.xlsx')
    fibre_lines_gpd = []
    for ruta in fibre.sitio.unique():
        stack_lonlat = fibre[fibre.sitio==ruta].agg({'lon': np.stack, 'lat':  np.stack})
        # Create the LineString using aggregate values
        lineStringObj = LineString(list(zip(*stack_lonlat)))
        df6 = pd.DataFrame()
        df6['RUTA'] = [ruta,]
        line_gdf = gpd.GeoDataFrame(df6, crs='epsg:4326', geometry=[lineStringObj,])
        fibre_lines_gpd.append(line_gdf)
    fibre_lines_gpd =pd.concat(fibre_lines_gpd )
    crs = {'init':'epsg:4326'}
    geometry = [Point(xy) for xy in zip(fibre['lon'],fibre['lat'])]
    fibre = gpd.GeoDataFrame(fibre.drop(columns='geometry'),  
                             crs=crs,
                             geometry=geometry)
    
    return fibre, fibre_lines_gpd

@st.cache_data
def line_gdp_df():
    fibre_fttb = pd.read_excel('data/ruta_de_fibra_fttb.xlsx')
    fibre_fttb_for_ranking = fibre_fttb.sitio.value_counts().reset_index()
    fibre_fttb_for_lines = fibre_fttb_for_ranking[fibre_fttb_for_ranking.sitio != 1]
    fibre_fttb_for_points = fibre_fttb_for_ranking[fibre_fttb_for_ranking.sitio == 1]['index'].unique()
    fibre_fttb_lines_gpd = []
    for ruta in fibre_fttb_for_lines['index'].unique():
        stack_lonlat = fibre_fttb[fibre_fttb.sitio==ruta].agg({'lon': np.stack, 'lat':  np.stack})
        # Create the LineString using aggregate values
        lineStringObj = LineString(list(zip(*stack_lonlat)))
        df6 = pd.DataFrame()
        df6['RUTA'] = [ruta,]
        line_gdf = gpd.GeoDataFrame(df6, crs='epsg:4326', geometry=[lineStringObj,])
        fibre_fttb_lines_gpd.append(line_gdf)
    fibre_fttb_lines_gpd =pd.concat(fibre_fttb_lines_gpd )
    return fibre_fttb_lines_gpd, fibre_fttb[fibre_fttb.sitio.isin(fibre_fttb_for_points)]

@st.cache_data
def el_salvador_map_df():
    #sv_admin_boundaries_0 = gpd.read_file('data\others\slv_admbnda_adm0_gadm_20210204.shp')
    sv_admin_boundaries_1 = gpd.read_file('data/slv_admbnda_adm1_gadm_20210204.shp')
    sv_admin_boundaries_2 = gpd.read_file('data/slv_admbnda_adm2_gadm_20210204.shp')
    #sv_admin_boundaries_all = gpd.read_file('data\others\slv_admbndp_admALL_gadm_itos_20210204.shp')
    el_salvador_map = pd.concat([#sv_admin_boundaries_0,
                                #sv_admin_boundaries_1,
                                sv_admin_boundaries_2,
                                #sv_admin_boundaries_all
                                ])
    
    el_salvador_map['ADM1_ES'] = el_salvador_map['ADM1_ES'].str.upper().str.replace('Á','A').str.replace('É','E').str.replace('Í','I').str.replace('Ó','O').str.replace('Ú','U')
    el_salvador_map['ADM2_ES'] = el_salvador_map['ADM2_ES'].str.upper().str.replace('Á','A').str.replace('É','E').str.replace('Í','I').str.replace('Ó','O').str.replace('Ú','U')
    return el_salvador_map,sv_admin_boundaries_2,sv_admin_boundaries_1



# CONNECTION TO GOOGLE MAPS

API_KEY=st.secrets["db_username"]
gmaps =  googlemaps.Client(key=API_KEY)

@st.cache_data
def lead_generator(location,type,distance): 
    
    business_list = []
    try: 
        response = gmaps.places_nearby(
                                        location=location,
                                        radius=distance,
                                        open_now=False,
                                        language="es-419",
                                        keyword =type
                                        )

        business_list.extend(response.get('results'))
        next_page_token = response.get('next_page_token')


        while next_page_token:
            time.sleep(3)
            response = gmaps.places_nearby(
                                            location=location,
                                            radius=distance,
                                            open_now=False,
                                            language="es-419",
                                            keyword=type,
                                            page_token=next_page_token
                                            )
            business_list.extend(response.get('results'))
            next_page_token = response.get('next_page_token')
            
        df = pd.DataFrame(business_list)
    
        place_detail_df = []

        for place in df.place_id:
            my_fields = [
                            'name',
                            'place_id',
                            'type',
                            'formatted_address',
                            'icon',
                            'formatted_phone_number',
                            'website',
                            'rating',
                            'vicinity',
                            'geometry'
                        ]
            place_details = gmaps.place(place_id=place, fields=my_fields)
            place_detail_df.append(pd.DataFrame(json_normalize(place_details)))
        
        column_rename = {
                            'result.formatted_address':'address',
                            'result.geometry.location.lat':'lat',
                            'result.geometry.location.lng':'lng',
                            'result.geometry.viewport.northeast.lat':'northeast.lat',
                            'result.geometry.viewport.northeast.lng':'northeast.lng',
                            'result.geometry.viewport.southwest.lat':'southwest.lat',
                            'result.geometry.viewport.southwest.lng':'southwest.lng',
                            'result.icon':'icon',
                            'result.name':'name',
                            'result.place_id':'place_id',
                            'result.rating':'rating',
                            'result.types':'types',
                            'result.vicinity':'vicinity',
                            'result.formatted_phone_number':'telefono_contacto'
                        }
            
        places_detail_df_final = pd.concat(place_detail_df).rename(columns=column_rename)

        places_detail_df_final['given_coordinates'] = location
        places_detail_df_final['tipo_comercio'] = type
        places_detail_df_final['radius'] = distance
        if 'name' in list(places_detail_df_final.columns):
            places_detail_df_final['name'] = places_detail_df_final['name']
        else:
            places_detail_df_final['name'] = 'NO DISPONIBLE' 
            
        if 'place_id' in list(places_detail_df_final.columns):
            places_detail_df_final['place_id'] = places_detail_df_final['place_id']
        else:
            places_detail_df_final['place_id'] = 'NO DISPONIBLE' 
            
        if 'status' in list(places_detail_df_final.columns):
            places_detail_df_final['status'] = places_detail_df_final['status']
        else:
            places_detail_df_final['status'] = 'NO DISPONIBLE' 
            
        if 'vicinity' in list(places_detail_df_final.columns):
            places_detail_df_final['vicinity'] = places_detail_df_final['vicinity']
        else:
            places_detail_df_final['vicinity'] = 'NO DISPONIBLE' 
            
        if 'address' in list(places_detail_df_final.columns):
            places_detail_df_final['address'] = places_detail_df_final['address']
        else:
            places_detail_df_final['address'] = 'NO DISPONIBLE' 
            
        if 'rating' in list(places_detail_df_final.columns):
            places_detail_df_final['rating'] = places_detail_df_final['rating']
        else:
            places_detail_df_final['rating'] = 'NO DISPONIBLE' 
            
        if 'website' in list(places_detail_df_final.columns):
            places_detail_df_final['website'] = places_detail_df_final['website']
        else:
            places_detail_df_final['website'] = 'NO DISPONIBLE' 
            
        if 'telefono_contacto' in list(places_detail_df_final.columns):
            places_detail_df_final['telefono_contacto'] = places_detail_df_final['telefono_contacto']
        else:
            places_detail_df_final['telefono_contacto'] = 'NO DISPONIBLE' 
            
        if 'types' in list(places_detail_df_final.columns):
            places_detail_df_final['types'] = places_detail_df_final['types']
        else:
            places_detail_df_final['types'] = 'NO DISPONIBLE' 
            
        if 'lat' in list(places_detail_df_final.columns):
            places_detail_df_final['lat'] = places_detail_df_final['lat']
        else:
            places_detail_df_final['lat'] = 'NO DISPONIBLE' 
            
        if 'lng' in list(places_detail_df_final.columns):
            places_detail_df_final['lng'] = places_detail_df_final['lng']
        else:
            places_detail_df_final['lng'] = 'NO DISPONIBLE'
            
        if 'northeast.lat' in list(places_detail_df_final.columns):
            places_detail_df_final['northeast.lat'] = places_detail_df_final['northeast.lat']
        else:
            places_detail_df_final['northeast.lat'] = 'NO DISPONIBLE' 
            
        if 'northeast.lng' in list(places_detail_df_final.columns):
            places_detail_df_final['northeast.lng'] = places_detail_df_final['northeast.lng']
        else:
            places_detail_df_final['northeast.lng'] = 'NO DISPONIBLE' 
            
        if 'southwest.lat' in list(places_detail_df_final.columns):
            places_detail_df_final['southwest.lat'] = places_detail_df_final['southwest.lat']
        else:
            places_detail_df_final['southwest.lat'] = 'NO DISPONIBLE' 
            
        if 'southwest.lng' in list(places_detail_df_final.columns):
            places_detail_df_final['southwest.lng'] = places_detail_df_final['southwest.lng']
        else:
            places_detail_df_final['southwest.lng'] = 'NO DISPONIBLE' 
            

        places_detail_df_final = places_detail_df_final[[
                                                            'given_coordinates',
                                                            'tipo_comercio',
                                                            'radius',
                                                            'name',
                                                            'place_id',
                                                            'status',
                                                            'vicinity',
                                                            'address',
                                                            'rating',
                                                            'website',
                                                            'telefono_contacto',
                                                            'types',
                                                            'lat', 
                                                            'lng',
                                                            'northeast.lat',
                                                            'northeast.lng',
                                                            'southwest.lat',
                                                            'southwest.lng',
                                                        ]]
        
        crs = {'init':'epsg:4326'}
        geometry = [Point(xy) for xy in zip(places_detail_df_final['lng'],places_detail_df_final['lat'])]
        places_detail_df_final = gpd.GeoDataFrame(places_detail_df_final,
                                    crs=crs,
                                    geometry=geometry)
        places_detail_df_final = ckdnearest(places_detail_df_final.rename(columns={'lat':'lat_cliente',
                                          'lng':'lon_cliente'}), 
                 gpd.GeoDataFrame(fibre,geometry=gpd.points_from_xy(fibre.lon, fibre.lat),crs={'init' :'epsg:4326'}).rename(columns={'lat':'lat_fibra',
                                                                                                                                    'lon':'lon_fibra'}))
        tuples_ruta = [(xy) for xy in zip(places_detail_df_final['lat_fibra'].astype(float),places_detail_df_final['lon_fibra'].astype(float))]
        tuples_cliente = [(xy) for xy in zip(places_detail_df_final['lat_cliente'].astype(float),places_detail_df_final['lon_cliente'].astype(float))]  
        distances_final = []
        for coordinates_cliente, coordinates_fibre in zip(tuples_ruta,tuples_cliente):
            distances = geopy.distance.geodesic(coordinates_cliente, coordinates_fibre).m
            distances_final.append(distances)
        
        places_detail_df_final['distances_final_fibra'] = distances_final
        
        
        return places_detail_df_final
    
    except:
        pass
    
def folium_map(df, selection):
    folium_parameters = { 'location':[13.73022, -88.86712],      
            'zoom_start':9,
            'attr':'MAPBOX',
            #'width':1000,
            #'height':600,
            'control_scale':True,
            'tiles': 'https://api.mapbox.com/styles/v1/fjcoreas/cl5fm2i0q000t14ptxd2fd78j/tiles/256/{z}/{x}/{y}@2x?access_token=pk.eyJ1IjoiZmpjb3JlYXMiLCJhIjoiY2w1ZmxycHY5MWNmeDNvbXQ4dGwwZ3FscyJ9.CkpPn4ExUV7tzpKHBc7rUw',
            'name':'MAPBOX TILE'
            }

    #style_function = lambda x: {'fillColor': '#ffffff', 
    #                            'color':'#000000', 
    #                            'fillOpacity': 0.1, 
    #                            'weight': 0.1}
    #highlight_function = lambda x: {'fillColor': '#000000', 
    #                                'color':'#000000', 
    #                                'fillOpacity': 0.50, 
    #                                'weight': 0.1}

    if selection=='USER INPUT':
        
        m = folium.Map(**folium_parameters)

        fibre_lines = folium.Choropleth(
            fttb_fibregeojsons,
            line_weight=4,
            line_color='deeppink',
            name = 'FIBRE LINES' 
        ).add_to(m)
        
        fttb_line = folium.Choropleth(
            fttb_geojsons_nopoints[['Name','description','geometry']],
            line_weight=4,
            line_color='mediumblue',
            name = 'FTTB LINES'
        ).add_to(m)
        
        fttb2_line = folium.Choropleth(
            fttb_fibregeojsons_2[~fttb_fibregeojsons_2.geometry.astype(str).str.lower().str.contains('point',na=False)],
            line_weight=4,
            line_color='purple',
            fill=False,
            name = 'FTTB LINES 2'
        ).add_to(m)
        
        fttb_line.geojson.add_child(
        folium.features.GeoJsonTooltip(fields=['description', 'Name'],
                                       aliases=['Description: ', 'Name: '],
                                       style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"))) # setting style for popup box
        
        
        
        fibre_lines.geojson.add_child(
        folium.features.GeoJsonTooltip(fields=['description', 'Name'],
                                       aliases=['Description: ', 'Name: '],
                                       style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"))) # setting style for popup box
        
        #fttb2_line.geojson.add_child(
        #folium.features.GeoJsonTooltip(fields=['Field_1', 'Type', 'Country', 'Comments', 'SHAPE', 'LABEL', 'Name', 'Eqpt_Label'],
        #                               aliases=['Field_1: ', 'Type: ', 'Country: ', 'Comments: ', 'SHAPE: ', 'LABEL: ', 'Name: ', 'Eqpt_Label: '],
        #                               style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"))) # setting style for popup box



        shapelayer_distance = folium.FeatureGroup(name="Distancia Fibra",show=False).add_to(m)
        shapesLayer_borders = folium.FeatureGroup(name="Borders El Salvador",show=False).add_to(m)
        shapesLayer_borders_municipios = folium.FeatureGroup(name="Borders Municipios",show=False).add_to(m)
        fttb_unkown = folium.FeatureGroup(name="FTTB KEY POINTS",show=False).add_to(m)

        for _, r in sv_admin_boundaries_1.iterrows():
            # Without simplifying the representation of each borough,
            # the map might not be displayed
            sim_geo = gpd.GeoSeries(r['geometry']).simplify(tolerance=0.001)
            geo_j = sim_geo.to_json()
            geo_j = folium.GeoJson(data=geo_j,
                                style_function=lambda x: {'color': 'darkslategray',
                                                            'dashArray':4,
                                                            'weight':2.0,
                                                            'control':False,
                                                            'fill':False,
                                                            'name':'Country Borders'})
            folium.Popup(r['ADM1_ES']).add_to(geo_j)
            geo_j.add_to(shapesLayer_borders)

        for _, r in sv_admin_boundaries_2.iterrows():
            # Without simplifying the representation of each borough,
            # the map might not be displayed
            sim_geo_2 = gpd.GeoSeries(r['geometry']).simplify(tolerance=0.001)
            geo_j_2 = sim_geo_2.to_json()
            geo_j_2 = folium.GeoJson(data=geo_j_2,
                                style_function=lambda x: {'color': 'darkslategray',
                                                            'dashArray':4,
                                                            'weight':2.0,
                                                            'control':False,
                                                            'fill':False,
                                                            'name':'Country Borders'})
        folium.Popup(r['ADM2_ES']).add_to(geo_j_2)
        geo_j_2.add_to(shapesLayer_borders_municipios)
        
        for ix, row in fttb_geojsons_points.iterrows():
            folium.CircleMarker(location = [row['lat'],row['lon']],
                                radius=5,
                                color='mediumblue', 
                                fill_color='mediumblue',
                                popup = f"<strong>{row.Name}</strong><br><strong>Description: </strong>{row.description}", 
                        ).add_to(fttb_unkown)
            
        for ix, row in df.iterrows():
            folium.CircleMarker(location = [row['lat_fibra'],row['lon_fibra']],
                                radius=3,
                                color='gray', 
                                fill_color='gray',
                                popup = f"<strong>{row.sitio}</strong><br><strong>Lat, Lon: </strong>{row.lat_fibra}, {row.lon_fibra}</br>", 
                        ).add_to(m)
            
        for ix, row in df.iterrows():
            folium.Marker(location = [row['lat_cliente'],row['lon_cliente']],
                        icon=folium.Icon(color='pink',icon_color='white',icon='user',prefix='fa'),
                        popup = f"<strong>{row.nombre}</strong><br></br> <strong>Distancia Fibra: </strong>{row.distances_final_fibra:,.0f} metros<br></br>", 
                        ).add_to(m)
            
        for ix, row in df.iterrows():
            folium.PolyLine(locations = [ 
                                        [row['lat_cliente'],
                                        row['lon_cliente']], 
                                        [row['lat_fibra'], 
                                        row['lon_fibra']] 
                                        ],
                                weight=5,
                                #tooltip =  f"NOMBRE DE ESCUELA: {row.nombre_de_centro_escolar}, COSTO CAPEX: {row.capex_total:,.2f}, CATEGORIA 3G: {row.categoria_cobertura_3g}, CATEGORIA LTE: {row.categoria_cobertura_lte}" ,
                                tooltip = f"<b>DISTANCE:{row.distances_final_fibra:,.0f} meters </br>",   
                                dash_array='5',
                                color='green', 
                            ).add_to(shapelayer_distance)
            
        popup1 = folium.LatLngPopup()
        minimap = plugins.MiniMap(toggle_display=True,position='bottomright')
        m.add_child(minimap)
        m.add_child(popup1)
        draw = plugins.Draw(export=True)
        draw.add_to(m)
        plugins.Fullscreen(position='topright').add_to(m)   
        folium.raster_layers.TileLayer('CartoDB Positron').add_to(m)
        folium.LayerControl().add_to(m)
            
    elif selection == 'GOOGLE':
        m = folium.Map(**folium_parameters)

        fibre_lines = folium.Choropleth(
            fttb_fibregeojsons,
            line_weight=4,
            line_color='deeppink',
            name = 'FIBRE LINES' 
        ).add_to(m)
        
        fttb_line = folium.Choropleth(
            fttb_geojsons_nopoints[['Name','description','geometry']],
            line_weight=4,
            line_color='mediumblue',
            name = 'FTTB LINES'
        ).add_to(m)
        
        fttb2_line = folium.Choropleth(
            fttb_fibregeojsons_2,
            line_weight=4,
            line_color='purple',
            name = 'FTTB LINES'
        ).add_to(m)
        
        fttb_line.geojson.add_child(
        folium.features.GeoJsonTooltip(fields=['description', 'Name'],
                                       aliases=['Description: ', 'Name: '],
                                       style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"))) # setting style for popup box
        
        
        
        fibre_lines.geojson.add_child(
        folium.features.GeoJsonTooltip(fields=['description', 'Name'],
                                       aliases=['Description: ', 'Name: '],
                                       style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"))) # setting style for popup box
        
        fttb2_line.geojson.add_child(
        folium.features.GeoJsonTooltip(fields=['description', 'Name'],
                                       aliases=['Description: ', 'Name: '],
                                       style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"))) # setting style for popup box
        
        shapelayer_distance = folium.FeatureGroup(name="Distancia Fibra",show=False).add_to(m)
        shapesLayer_borders = folium.FeatureGroup(name="Borders El Salvador",show=False).add_to(m)
        shapesLayer_borders_municipios = folium.FeatureGroup(name="Borders Municipios",show=False).add_to(m)
        fttb_unkown = folium.FeatureGroup(name="FTTB KEY POINTS",show=False).add_to(m)

        for _, r in sv_admin_boundaries_1.iterrows():
            # Without simplifying the representation of each borough,
            # the map might not be displayed
            sim_geo = gpd.GeoSeries(r['geometry']).simplify(tolerance=0.001)
            geo_j = sim_geo.to_json()
            geo_j = folium.GeoJson(data=geo_j,
                                style_function=lambda x: {'color': 'darkslategray',
                                                            'dashArray':4,
                                                            'weight':2.0,
                                                            'control':False,
                                                            'fill':False,
                                                            'name':'Country Borders'})
            folium.Popup(r['ADM1_ES']).add_to(geo_j)
            geo_j.add_to(shapesLayer_borders)

        for _, r in sv_admin_boundaries_2.iterrows():
            # Without simplifying the representation of each borough,
            # the map might not be displayed
            sim_geo_2 = gpd.GeoSeries(r['geometry']).simplify(tolerance=0.001)
            geo_j_2 = sim_geo_2.to_json()
            geo_j_2 = folium.GeoJson(data=geo_j_2,
                                style_function=lambda x: {'color': 'darkslategray',
                                                            'dashArray':4,
                                                            'weight':2.0,
                                                            'control':False,
                                                            'fill':False,
                                                            'name':'Country Borders'})
            folium.Popup(r['ADM2_ES']).add_to(geo_j_2)
            geo_j_2.add_to(shapesLayer_borders_municipios)      
        
        for ix, row in fttb_geojsons_points.iterrows():
            folium.CircleMarker(location = [row['lat'],row['lon']],
                                radius=5,
                                color='mediumblue', 
                                fill_color='mediumblue',
                                popup = f"<strong>{row.Name}</strong><br><strong>Description: </strong>{row.description}", 
                        ).add_to(fttb_unkown) 
        
        for ix, row in df.iterrows():
            folium.CircleMarker(location = [row['lat_fibra'],row['lon_fibra']],
                                radius=3,
                                color='gray', 
                                fill_color='gray',
                                popup = f"<strong>{row.sitio}</strong><br><strong>Lat, Lon: </strong>{row.lat_fibra}, {row.lon_fibra}</br>", 
                        ).add_to(m)
            
        for ix, row in df.iterrows():
            folium.Marker(location = [row['lat_cliente'],row['lon_cliente']],
                        icon=folium.Icon(color='pink',icon_color='white',icon='user',prefix='fa'),
                        popup = f"<strong>{row.client_name}</strong><br></br> <strong>Distancia Fibra: </strong>{row.distances_final_fibra:,.0f} metros<br></br><strong>Telefono:</strong>{row.telefono_contacto}<br></br><strong>Direccion: </strong>{row.address}<br></br>", 
                        ).add_to(m)
            
        for ix, row in df.iterrows():
            folium.PolyLine(locations = [ 
                                        [row['lat_cliente'],
                                        row['lon_cliente']], 
                                        [row['lat_fibra'], 
                                        row['lon_fibra']] 
                                        ],
                                weight=5,
                                #tooltip =  f"NOMBRE DE ESCUELA: {row.nombre_de_centro_escolar}, COSTO CAPEX: {row.capex_total:,.2f}, CATEGORIA 3G: {row.categoria_cobertura_3g}, CATEGORIA LTE: {row.categoria_cobertura_lte}" ,
                                tooltip = f"<b>DISTANCE:{row.distances_final_fibra:,.0f} meters </br>",   
                                dash_array='5',
                                color='green', 
                            ).add_to(shapelayer_distance)
        popup1 = folium.LatLngPopup()
        minimap = plugins.MiniMap(toggle_display=True,position='bottomright')
        m.add_child(minimap)
        m.add_child(popup1)
        draw = plugins.Draw(export=True)
        draw.add_to(m)
        plugins.Fullscreen(position='topright').add_to(m)   
        folium.raster_layers.TileLayer('CartoDB Positron').add_to(m)
        folium.LayerControl().add_to(m)
    
    elif selection == 'INITIAL':

        m = folium.Map(**folium_parameters)

        fibre_lines = folium.Choropleth(
            fttb_fibregeojsons,
            line_weight=4,
            line_color='deeppink',
            name = 'FIBRE LINES' 
        ).add_to(m)
        
        fttb_line = folium.Choropleth(
            fttb_geojsons_nopoints[['Name','description','geometry']],
            line_weight=4,
            line_color='mediumblue',
            name = 'FTTB LINES'
        ).add_to(m)
        
        fttb2_line = folium.Choropleth(
            fttb_fibregeojsons_2,
            line_weight=4,
            line_color='purple',
            name = 'FTTB LINES'
        ).add_to(m)

        fttb_line.geojson.add_child(
        folium.features.GeoJsonTooltip(fields=['description', 'Name'],
                                       aliases=['Description: ', 'Name: '],
                                       style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"))) # setting style for popup box
        
        
        
        fibre_lines.geojson.add_child(
        folium.features.GeoJsonTooltip(fields=['description', 'Name'],
                                       aliases=['Description: ', 'Name: '],
                                       style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"))) # setting style for popup box
        
        fttb2_line.geojson.add_child(
        folium.features.GeoJsonTooltip(fields=['description', 'Name'],
                                       aliases=['Description: ', 'Name: '],
                                       style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")
                                       )) # setting style for popup box
        
        shapelayer_distance = folium.FeatureGroup(name="Distancia Fibra",show=False).add_to(m)
        shapesLayer_borders = folium.FeatureGroup(name="Borders El Salvador",show=False).add_to(m)
        shapesLayer_borders_municipios = folium.FeatureGroup(name="Borders Municipios",show=False).add_to(m)
        fttb_unkown = folium.FeatureGroup(name="FTTB KEY POINTS",show=False).add_to(m)
        
        for _, r in sv_admin_boundaries_1.iterrows():
            # Without simplifying the representation of each borough,
            # the map might not be displayed
            sim_geo = gpd.GeoSeries(r['geometry']).simplify(tolerance=0.001)
            geo_j = sim_geo.to_json()
            geo_j = folium.GeoJson(data=geo_j,
                                style_function=lambda x: {'color': 'darkslategray',
                                                            'dashArray':4,
                                                            'weight':2.0,
                                                            'control':False,
                                                            'fill':False,
                                                            'name':'Country Borders'})
            folium.Popup(r['ADM1_ES']).add_to(geo_j)
            geo_j.add_to(shapesLayer_borders)

        for _, r in sv_admin_boundaries_2.iterrows():
            # Without simplifying the representation of each borough,
            # the map might not be displayed
            sim_geo_2 = gpd.GeoSeries(r['geometry']).simplify(tolerance=0.001)
            geo_j_2 = sim_geo_2.to_json()
            geo_j_2 = folium.GeoJson(data=geo_j_2,
                                style_function=lambda x: {'color': 'darkslategray',
                                                            'dashArray':4,
                                                            'weight':2.0,
                                                            'control':False,
                                                            'fill':False,
                                                            'name':'Country Borders'})
            folium.Popup(r['ADM2_ES']).add_to(geo_j_2)
            geo_j_2.add_to(shapesLayer_borders_municipios) 
            
        for ix, row in fttb_geojsons_points.iterrows():
            folium.CircleMarker(location = [row['lat'],row['lon']],
                                radius=5,
                                color='mediumblue', 
                                fill_color='mediumblue',
                                popup = f"<strong>{row.Name}</strong><br><strong>Description: </strong>{row.description}", 
                        ).add_to(fttb_unkown)

        popup1 = folium.LatLngPopup()
        minimap = plugins.MiniMap(toggle_display=True,position='bottomright')
        m.add_child(minimap)
        m.add_child(popup1)
        draw = plugins.Draw(export=True)
        draw.add_to(m)
        plugins.Fullscreen(position='topright').add_to(m)   
        folium.raster_layers.TileLayer('CartoDB Positron').add_to(m)
        folium.LayerControl().add_to(m)

    return m

# APP BUILD

fibre, fibre_lines_gpd = linestring_fibre()

#fibre_fttb_lines_gpd,fibre_fttb = line_gdp_df()

el_salvador_map,sv_admin_boundaries_2,sv_admin_boundaries_1 = el_salvador_map_df()

fttb_fibregeojsons,fttb_geojsons,fttb_fibregeojsons_2 = read_geojsons()

geo_type = []
for geo in fttb_geojsons.geometry:
    geo_type.append(type(geo))
    
fttb_geojsons['geometry_type'] = geo_type
fttb_geojsons_points = fttb_geojsons[fttb_geojsons.geometry_type.astype(str).str.lower().str.contains('poi',na=False)]
fttb_geojsons_nopoints = fttb_geojsons[~fttb_geojsons.geometry_type.astype(str).str.lower().str.contains('poi',na=False)]
fttb_geojsons_points['lon'] = fttb_geojsons_points['geometry'].x
fttb_geojsons_points['lat'] = fttb_geojsons_points['geometry'].y


df_fibreline_deps = gpd.sjoin_nearest(
                            fibre_lines_gpd,
                            el_salvador_map,
                            how='left',
                           )

st.sidebar.header('Seleccionar opciones: ')

opciones_ = st.sidebar.radio(
                                "Seleccione la opcion",
                                (
                                '1 ubicacion', 
                                 'Mas de 1 ubicacion',
                                 'Buscar comercios'
                                 )
    )  

if opciones_ == '1 ubicacion':
    st.subheader('Completar informacion solicitada y presionar el boton de Agregar al terminar')
    with st.form('my_form', clear_on_submit=False):
        col1,col2,col3 = st.columns(3)
        nombre_cliente = col1.text_input("Insertar nombre del Cliente: ", "Oficinas Digicel El Salvador")
        latitud = col2.text_input("Latitud: ", 13.671648)
        longitud = col3.text_input("Longitud: ", -89.257372) 
        submitted = st.form_submit_button('Agregar')
        if submitted:
            dictionary_clientes = {
                'nombre':[nombre_cliente],
                'lat_cliente':[float(latitud)],
                'lon_cliente':[float(longitud)]
            }
            
            df_coordenadas_clientes = pd.DataFrame.from_dict(dictionary_clientes)
            df_coordenadas_clientes['tamano'] = 5
            
            
            
            
            nearest_df_fibra = ckdnearest(gpd.GeoDataFrame(df_coordenadas_clientes,geometry=gpd.points_from_xy(df_coordenadas_clientes.lon_cliente, df_coordenadas_clientes.lat_cliente),crs={'init' :'epsg:4326'}), 
                                          fibre).rename(columns={'lat':'lat_fibra',
                                                                                                           'lon':'lon_fibra'})
            
            
            tuples_nodo = [(xy) for xy in zip(nearest_df_fibra['lat_fibra'].astype(float),nearest_df_fibra['lon_fibra'].astype(float))]
            tuples_cliente = [(xy) for xy in zip(nearest_df_fibra['lat_cliente'].astype(float),nearest_df_fibra['lon_cliente'].astype(float))]
            
            ditances_final = []
            for coordinates_cliente, coordinates_fibre in zip(tuples_nodo,tuples_cliente):
                #print(tuple(coordinates_schools),tuple(coordinates_fibre))
                distances = geopy.distance.geodesic(coordinates_cliente, coordinates_fibre).m
                ditances_final.append(distances)
            nearest_df_fibra['distances_final_fibra'] = ditances_final
            nearest_df_fibra = nearest_df_fibra[['nombre',
                                                'lat_cliente',
                                                'lon_cliente',
                                                'tamano',
                                                #'geometry',
                                                'sitio',
                                                #'SiteName',
                                                'lat_fibra',
                                                'lon_fibra',
                                                'distances_final_fibra']]
            #AgGrid(
            #        pd.DataFrame(nearest_df_fibra),
            #        height=100,
            #        theme='alpine',
            #        #fit_columns_on_grid_load=True,
            #        width='80%'
            #    
            #    )
            
            
            
            m = folium_map(pd.DataFrame(nearest_df_fibra), selection='USER INPUT')
            
            #col1,col2 = st.columns(2)    
            
            with st.container():
            
                folium_static(m, width=width, height=height)
                
elif opciones_ == 'Mas de 1 ubicacion':
    st.subheader('1. Descarga formato para completar con coordenadas del cliente: ')
    st.write('  -    Agrega el nombre del cliente o de las ubicaciones donde el cliente requiere el servicio')
    st.write('  -    Agrega la Latitud (lat_cliente) y Longitud (lon_cliente) en formato numerico')
    st.write('  -    Agregale el telefono si lo tienes')
    st.write('  -    Agregale la direccion si lo tienes')
    df = pd.read_excel('output_data/format_input.xlsx')
    
    df_xlsx = to_excel(df)
    
    st.download_button(label='📥 Descargar formato a utilizar',
                                        data=df_xlsx ,
                                        file_name= 'coordenadas_cliente.xlsx') 
    
    st.subheader('2. Adjunta el archivo que acabas de completar')
    
    uploaded_file = st.file_uploader("")
    if uploaded_file is not None:
     # To read file as bytes:
        df_coordenadas_clientes = pd.read_excel(uploaded_file)
        df_coordenadas_clientes[['lat_cliente','lon_cliente',]] = df_coordenadas_clientes[['lat_cliente','lon_cliente']].astype(float)
        #coordenadas_clientes['tamano'] = pd.to_numeric(coordenadas_clientes['tamano'], errors='coerce')  
        #coordenadas_clientes['tamano_normalizado'] = np.where(coordenadas_clientes['tamano'].isna(),
        #                                                      3,
        #                                                      coordenadas_clientes['tamano'].clip(lower=5,upper=10))
        df_coordenadas_clientes.fillna(0,inplace=True)
        
        nearest_df_fibra = ckdnearest(gpd.GeoDataFrame(df_coordenadas_clientes,geometry=gpd.points_from_xy(df_coordenadas_clientes.lon_cliente, df_coordenadas_clientes.lat_cliente),crs={'init' :'epsg:4326'}), 
                                      fibre).rename(columns={'lat':'lat_fibra',
                                                            'lon':'lon_fibra'})
            
        
        tuples_nodo = [(xy) for xy in zip(nearest_df_fibra['lat_fibra'].astype(float),nearest_df_fibra['lon_fibra'].astype(float))]
        tuples_cliente = [(xy) for xy in zip(nearest_df_fibra['lat_cliente'].astype(float),nearest_df_fibra['lon_cliente'].astype(float))]       
        ditances_final = []
        for coordinates_cliente, coordinates_fibre in zip(tuples_nodo,tuples_cliente):
            distances = geopy.distance.geodesic(coordinates_cliente, coordinates_fibre).m
            ditances_final.append(distances)
        nearest_df_fibra['distances_final_fibra'] = ditances_final
        
        nearest_df_fibra = nearest_df_fibra[['nombre',
                                            'lat_cliente',
                                            'lon_cliente',
                                            'telefono',
                                            'direccion',
                                            'sitio',
                                            'lat_fibra',
                                            'lon_fibra',
                                            'distances_final_fibra'
                                            ]]
        AgGrid(
                    nearest_df_fibra,
                    theme='alpine',
                    #fit_columns_on_grid_load=True,
                    width='80%'
                
                )
        
        df_analisis = to_excel(nearest_df_fibra)
    
        st.download_button(label='📥 Descargar analisis',
                                        data=df_analisis,
                                        file_name= 'analisis_distancias_nodos.xlsx')
        

        with st.expander("Ver Mapa"):
            m = folium_map(pd.DataFrame(nearest_df_fibra), selection='USER INPUT')
            
            folium_static(m, width=width, height=height)
            
elif opciones_ == 'Buscar comercios':
    df_geo_1 = False
    m = folium_map(pd.DataFrame(), selection='INITIAL')
    with st.container():
        folium_static(m, width=width, height=height)
        
    st.subheader('Proveer informacion para realizar la busqueda en Google')
    with st.form('my_form', clear_on_submit=False):
        col1,col2,col3 = st.columns(3)
        categoria = col1.text_input("Insertar categoria de negocio: ",)
        radio = col2.number_input("Insertar radio de busqueda en metros: ", min_value=10, max_value=10_000, value=100, step=10)
        latitud = col3.text_input("Insertar Latitud de Punto de Referencia: ", )
        longitud = col3.text_input("Insertar Longitud de Punto de Referencia: ", )
        location=f"{latitud},{longitud}"
        submitted = st.form_submit_button('Buscar')
        if submitted:
            df_geo = lead_generator(location=location,
                                    type=categoria,
                                    distance=radio).rename(columns={'name':'client_name'}).drop(columns='geometry') 
            AgGrid(
                    pd.DataFrame(df_geo),
                    height=400,
                    theme='alpine',
                    #fit_columns_on_grid_load=True,
                    width='80%'
                
                )
            df_geo_1 = True
            
    if df_geo_1 == True:

        df_analisis = to_excel(df_geo)
        

        st.download_button(label='📥 Descargar analisis',
                                        data=df_analisis,
                                        file_name= 'analisis_distancias_nodos_google.xlsx')

        with st.expander("Ver Mapa"):
            m = folium_map(df_geo, selection='GOOGLE')
            
            folium_static(m, width=width, height=height)           