#%%
import pandas as pd
from shapely.geometry import Point, LineString, shape
import folium
from folium.features import DivIcon
from folium import plugins
import osmnx as ox
import networkx as nx
from pandas import json_normalize
import numpy as np
from itertools import groupby
import plotly.express as px
import datetime
import streamlit as st
from streamlit_folium import folium_static

# Parte para realizar el mapa interactivo
def number_DivIcon(color,number):
    icon = DivIcon(
            icon_size=(150,36),
            icon_anchor=(14,40),
            html="""<span class="fa-stack " style="font-size: 12pt" >>
                    <!-- The icon that will wrap the number -->
                    <span class="fa fa-circle-o fa-stack-2x" style="color : {:s}"></span>
                    <!-- a strong element with the custom content, in this case a number -->
                    <strong class="fa-stack-1x" style="color : #ffffff">
                         {:02d}  
                    </strong>
                </span>""".format(color,number)
        )
    return icon

rutas_f = pd.read_pickle("./rutas_f.pkl")
rutas = pd.read_pickle("./rutas.pkl")
vehiculos =pd.read_pickle("./vehiculos.pkl")
jobs =pd.read_pickle("./jobs.pkl")

st.set_page_config(layout='centered') #centered or wide
header_container = st.beta_container()

with header_container:
    st.header('Programando entrega de mercancías con Python')
    st.subheader('Carlos HG - galaviz@outlook.com')
    st.write('Una empresa local tiene que realizar 100 entregas en la \
        ciudad de Tampico a partir de las 9 am. Cuenta con 3 vehículos \
        cada uno con capacidad máxima de 40 entregas, cada entrega toma 5 minutos. Utilizando python  \
        y el optimizador VROOM, obtenemos lo siguiente:  \n \
        Un mapa interactivo con las entregas (marcadores rojos) y con la empresa (marcador gris)  \n  \
        Ruta vehículo 1 - Al este con 34 entregas y 35 viajes (viaje de regreso a empresa)  \n \
        Ruta vehículo 2 - Al sur con 40 entregas y 41 viajes  \n \
        Ruta vehículo 3 - Al noroeste con 26 entregas y 27 viajes')

    # mapa rutas
    max_0, min_0, max_1, min_1 = max(rutas_f['orig_loc'],key=lambda item:item[0])[0], min(rutas_f['orig_loc'],key=lambda item:item[0])[0], max(rutas_f['orig_loc'],key=lambda item:item[1])[1], min(rutas_f['orig_loc'],key=lambda item:item[1])[1]
    punto_central = ((max_1+min_1)/2, (max_0+min_0)/2)
    map_osm = folium.Map(location=punto_central, zoom_start=12)

    ox.config(use_cache=False, log_console=True)
    G = ox.graph_from_point(punto_central, dist=10000, network_type='drive', simplify=False)
    G = ox.speed.add_edge_speeds(G)
    G = ox.speed.add_edge_travel_times(G)

    # INICIO CREACION MAPA
    map_final = folium.Map(location=punto_central, zoom_start=13)
    # jobs en mapa
    jobs_layer = folium.FeatureGroup(name='Entregas')
    for index, row in jobs.iterrows():
        if index == 0:
            jobs_layer.add_child(folium.Marker(location=(row['LAT'], row['LONG']), popup=folium.Popup(folium.IFrame(html="""<b>ID: </b> {} </br> <b>Nombre: </b> {} """.format(row.NUM, row.NOMBRE), width=200, height=100)), icon=folium.Icon(color='black', icon='glyphicon-star'), width=200, height=100))
        else:
            jobs_layer.add_child(folium.Marker(location=(row['LAT'], row['LONG']), popup=folium.Popup(folium.IFrame(html="""<b>ID: </b> {} </br> <b>Nombre: </b> {} """.format(row.NUM, row.NOMBRE), width=200, height=100)), icon=folium.Icon(color='red', icon='shopping-cart')))
    map_final.add_child(jobs_layer)
    # lineas y marcadores de rutas en mapa
    for vehiculo in rutas_f.vehicle.unique():
        rutas_v = rutas_f.loc[rutas_f['vehicle'] == vehiculo]
        
        lineas_layer = folium.FeatureGroup(name='Vehículo '+str(vehiculo), show=False)    

        routes = []
        for index, row in rutas_v.iterrows():
            orig_loc = [row['orig_loc'][1], row['orig_loc'][0]]
            dest_loc = [row['dest_loc'][1], row['dest_loc'][0]]
            orig, dest = ox.get_nearest_node(G, orig_loc), ox.get_nearest_node(G, dest_loc)
            path = nx.shortest_path(G, orig, dest, weight='travel_time')
            routes.extend(path)

            lineas_layer.add_child(folium.Marker(location=dest_loc, icon=folium.Icon(color='black',icon_color='black')))
            lineas_layer.add_child(folium.Marker(location=dest_loc, popup=folium.Popup(folium.IFrame(html="""<b>ID: </b> {} </br> <b>Nombre: </b> {} """.format(row['dest_id'], row['dest_name']), width=200, height=100)), icon= number_DivIcon(row['VColor'], row['stop'])))

        routes = [x[0] for x in groupby(routes)]
        puntos = []
        for nodos in routes:
            puntos.append((G.nodes[nodos]['x'], G.nodes[nodos]['y']))
        
        puntos_swap = list(map(lambda t:(t[1],t[0]), puntos))
        linea_puntos = lineas_layer.add_child(folium.PolyLine(puntos_swap, color=vehiculos['Color_hex'][vehiculo-1]))
        attr = {'fill': 'black'}
        lineas_layer.add_child(plugins.PolyLineTextPath(linea_puntos, '\u25BA   ', repeat=True, attributes=attr))
        map_final.add_child(lineas_layer)
        
    folium.LayerControl(collapsed=False).add_to(map_final)
    folium_static(map_final)

    # Diagrama de Gantt
    hora_inicio = datetime.datetime(2021, 8, 16, 9,0,0)

    rutas_g = rutas[['type', 'vehicle', 'job', 'service', 'arrival']].fillna(0)
    rutas_g = rutas_g.merge(vehiculos[['id', 'Color_hex']], left_on='vehicle', right_on='id', how='left').rename(columns={'Color_hex':'VColor'}).drop(columns='id')
    rutas_g['arrival'] = hora_inicio + pd.to_timedelta(rutas_g['arrival'], unit='s')
    rutas_g['left'] = rutas_g['arrival'] + pd.to_timedelta(rutas_g['service'], unit='s')

    st.write('El diagrama de gantt muestra que:  \n \
            Vehículo 1 - Termina la última entrega a las 11:45  \n \
            Vehículo 2 - Termina la última entrega a las 13:15  \n \
            Vehículo 3 - Termina la última entrega a las 12:27  \n \
            Siento que el optimizador considera periodos de recorrido muy cortos, los tiempos los obtiene de openstreetmap')

    fig = px.timeline(rutas_g, x_start='arrival', x_end='left', y='vehicle', hover_name='job', color='VColor', color_discrete_map='identity')
    fig.update_yaxes(type='category')
    fig.update_layout(coloraxis_showscale=False)
    header_container.write(fig)

    st.write('Conclusiones:  \n \
        El optimizador VROOM es uno de varios existentes, aparte de calcular \
        la ruta óptima para entregas multi-vehículo tiene más fuciones que no \
        he explorado. En la versión demo deja calcular hasta 100 puntos, por eso \
        las 100 entregas del ejemplo.  \n \
        Aunque me costo trabajo realizar este proyecto, estoy sorprendido que \
        con solo 160 líneas de código y la información en excel, se puede lograr \
        un mapa que considero operacional para un escenario real.  \n \
        Links:  \n \
        https://verso-optim.com  \n \
        http://vroom-project.org  \n \
        https://www.openstreetmap.org/')
# %%
