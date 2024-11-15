import os
import csv
import folium
import geopandas as gpd
from folium.plugins import MarkerCluster
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
from collections import defaultdict
import plotly.express as px
from datetime import datetime, timedelta

# 날짜 설정
day_now = (datetime.today() - timedelta(9)).strftime("%Y-%m-%d")

# 데이터 경로 설정
data_input_dir = 'input\\01 data'
shp_input_dir = 'input\\02 shp'
station_file = os.path.join(data_input_dir, 'DRT정류장(통합).csv')
history_file = os.path.join(data_input_dir, '02_driving_history_20241025233451.csv')
shp_files = {
    "그린존": os.path.join(shp_input_dir, "청주_오송_그린존만.shp"),
    "레드존": os.path.join(shp_input_dir, "청주_오송_레드존.shp")
}

# 정류장 타입 구분
station_type = defaultdict(str)
try:
    with open(station_file, 'r', encoding='cp949') as f:
        reader = csv.reader(f)
        next(reader)  # 헤더 건너뛰기
        for row in reader:
            station_type[row[5]] = row[12]
except FileNotFoundError:
    print(f"Error: {station_file} 파일을 찾을 수 없습니다.")
except Exception as e:
    print(f"Error: {e}")

# Folium 지도 설정
m = folium.Map(location=[36.622693, 127.324673], zoom_start=13, width=755, height=600)
for name, path in shp_files.items():
    try:
        gdf = gpd.read_file(path)
        color = 'red' if name == "레드존" else 'green'
        folium.GeoJson(
            gdf,
            name=name,
            style_function=lambda x, color=color: {
                'fillColor': color,
                'color': color,
                'weight': 0.5,
                'fillOpacity': 0.1
            }
        ).add_to(m)
    except FileNotFoundError:
        print(f"Error: {path} 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"Error: {e}")

# 지도에 레이어 컨트롤 추가
folium.LayerControl().add_to(m)

# CSV 파일을 읽어 정류장별 승차 및 하차량 집계
in_count = defaultdict(int)     # 승차 집계
out_count = defaultdict(int)    # 하차 집계
sum_count = defaultdict(int)    # 총 이용량(승차+하차) 집계
call_count = defaultdict(int)   # 호출 현황
user_type_count = {"성인": 0, "청소년": 0, "어린이": 0}     # 이용자 유형 현황

try:
    with open(history_file, newline='', encoding='cp949') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # 헤더 건너뛰기

        for row in reader:
            num = int(row[7]) + int(row[8]) + int(row[9])

            if row[11] == day_now and row[10] == '이용완료':
                in_count[(row[19], float(row[23]), float(row[24]))] += num
                out_count[(row[20], float(row[25]), float(row[26]))] += num
                sum_count[(row[20], float(row[25]), float(row[26]))] += \
                    in_count[(row[19], float(row[23]), float(row[24]))] + out_count[
                        (row[20], float(row[25]), float(row[26]))]
                user_type_count["성인"] += int(row[7])
                user_type_count["청소년"] += int(row[8])
                user_type_count["어린이"] += int(row[9])

            call_count[row[10]] += 1

except FileNotFoundError:
    print(f"Error: {history_file} 파일을 찾을 수 없습니다.")
except Exception as e:
    print(f"Error: {e}")

# 지도에 정류장 데이터 추가
for station, lat, lon in in_count.keys():
    popup_text = f"<b>{station}</b><br>승차 : {in_count[(station, lat, lon)]}명, 하차 : {out_count.get((station, lat, lon), 0)}명"
    popup = folium.Popup(popup_text, max_width=300)
    color = 'red' if station_type[station] == '가상정류장' else 'blue'

    folium.Circle(
        location=[lat, lon],
        popup=popup,
        radius=sum_count[(station, lat, lon)] * 5,
        color=color,
        fill=True,
        fill_color=color
    ).add_to(m)

# Folium 지도를 HTML 파일로 저장
map_file = 'map.html'
m.save(map_file)

# Dash 앱 초기화
app = dash.Dash(__name__)

# Folium 지도 HTML 파일 읽기
with open(map_file, 'r', encoding='utf-8') as f:
    map_html = f.read()

# Dash 레이아웃 설정
app.layout = html.Div([
    # 상단 제목
    html.Div([
        html.H1("VARO DRT 지역별 현황"),
    ], style={'textAlign': 'center', 'padding': '1px'}),

    # 왼쪽 사이드바 및 지도
    html.Div([
        html.Div([
            dcc.Dropdown(
                id='region-dropdown',
                options=[{'label': '지역 1', 'value': 'region1'},
                         {'label': '지역 2', 'value': 'region2'}],
                value='region1'
            )
        ], style={'width': '20%', 'display': 'inline-block', 'padding': '5px'}),

        # 지도 및 그래프 배치
        html.Div([
            html.Iframe(srcDoc=map_html, width='100%', height='600', style={'display': 'inline-block', 'width': '60%'}),

            # 왼쪽 파이 차트
            html.Div([dcc.Graph(id="pie-chart", style={'height': '400px'})], style={'width': '33%', 'padding': '10px'}),

            # 중간 대기 시간 그래프 (막대형)
            html.Div([dcc.Graph(id="waiting-time-chart", style={'height': '400px'})],
                     style={'width': '33%', 'padding': '10px'}),

            # 오른쪽 수송 지표 그래프 (선형)
            html.Div([dcc.Graph(id="transport-metrics-chart", style={'height': '400px'})],
                     style={'width': '33%', 'padding': '10px'})

        ], style={'display': 'flex', 'width': '100%'})
    ])
])

# 지도 업데이트를 위한 callback
@app.callback(
    Output("map", "srcDoc"),  # HTML srcDoc을 업데이트
    Input("region-dropdown", "value")
)
def update_map(selected_region):
    # 지역별 초기 위치 설정 예시
    region_coordinates = {
        "region1": [36.610167, 127.324325],
        "region2": [36.622693, 127.324673],
    }

    # 기본 좌표: 선택한 지역이 없는 경우의 기본 지도 위치 설정
    center = region_coordinates.get(selected_region, [36.610167, 127.324325])

    # 새로운 Folium 지도 생성
    m = folium.Map(location=center, zoom_start=13, width=755, height=600)

    # 지역별 shapefile 경로 설정 예시 (필요에 따라 수정)
    shp_files = {
        "그린존": os.path.join(shp_input_dir, f"{selected_region}_그린존.shp"),
        "레드존": os.path.join(shp_input_dir, f"{selected_region}_레드존.shp")
    }

    # 지도에 폴리곤 추가
    for name, path in shp_files.items():
        try:
            gdf = gpd.read_file(path)
            color = 'red' if name == "레드존" else 'green'
            folium.GeoJson(
                gdf,
                name=name,
                style_function=lambda x, color=color: {
                    'fillColor': color,
                    'color': color,
                    'weight': 0.5,
                    'fillOpacity': 0.1
                }
            ).add_to(m)
        except FileNotFoundError:
            print(f"Error: {path} 파일을 찾을 수 없습니다.")
        except Exception as e:
            print(f"Error: {e}")

    # LayerControl 추가
    folium.LayerControl().add_to(m)

    # 정류장 정보 추가 (예시)
    for station, lat, lon in in_count.keys():
        popup_text = f"<b>{station}</b><br>승차 : {in_count[(station, lat, lon)]}명, 하차 : {out_count.get((station, lat, lon), 0)}명"
        popup = folium.Popup(popup_text, max_width=300)
        color = 'red' if station_type[station] == '가상정류장' else 'blue'

        folium.Circle(
            location=[lat, lon],
            popup=popup,
            radius=sum_count[(station, lat, lon)] * 5,
            color=color,
            fill=True,
            fill_color=color
        ).add_to(m)

    # Folium 지도를 HTML 파일로 저장 후 읽기
    updated_map_file = 'updated_map.html'
    m.save(updated_map_file)

    with open(updated_map_file, 'r', encoding='utf-8') as f:
        return f.read()

# 파이 차트 렌더링 콜백
@app.callback(
    Output("pie-chart", "figure"),
    Input("pie-chart", "id")
)
def display_pie_chart(_):
    labels = list(call_count.keys())
    values = list(call_count.values())
    fig = px.pie(
        names=labels,
        values=values,
        title="호출 현황",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    return fig

# 대기 시간 그래프 콜백
@app.callback(
    Output("waiting-time-chart", "figure"),
    Input("region-dropdown", "value")  # 필요 시 추가 Input 사용
)
def update_waiting_time_chart(selected_region):
    # 예시 데이터: 일주일 평균 대기 시간을 설정
    dates = [(datetime.today() - timedelta(i)).strftime("%Y-%m-%d") for i in range(7)]
    avg_waiting_times = [waiting_time_avg.get(date, 0) for date in dates]

    # 막대형 차트 생성
    fig = px.bar(
        x=dates,
        y=avg_waiting_times,
        labels={'x': 'Date', 'y': 'Average Waiting Time'},
        title="일주일 평균 대기시간"
    )
    return fig

# 수송 지표 그래프 콜백
@app.callback(
    Output("transport-metrics-chart", "figure"),
    Input("region-dropdown", "value")  # 필요 시 추가 Input 사용
)
def update_transport_metrics_chart(selected_region):
    # 예시 데이터: 수송 지표 데이터를 준비
    metrics = ['Metric 1', 'Metric 2', 'Metric 3']
    values = [100, 150, 130]  # 실제 데이터로 교체 필요

    # 선형 차트 생성
    fig = px.line(
        x=metrics,
        y=values,
        labels={'x': 'Metric', 'y': 'Value'},
        title="수송 지표"
    )
    return fig

# 앱 실행
if __name__ == '__main__':
    app.run_server(debug=True)

# 지역별 지도 설정 함수
# def create_map(region_name):
#     # 각 지역에 맞는 중심 좌표와 shapefile을 설정
#     center_coords = {
#         "오송": [36.622693, 127.324673],
#         "남이": [36.566559, 127.428627]
#     }
#
#     # 지역 중심이 없으면 기본 좌표로 설정
#     center = center_coords.get(region_name, [36.610167, 127.324325])
#
#     # folium 지도 생성
#     m = folium.Map(location=center, zoom_start=13, width="100%", height="600px")
#
#     # 예시 레이어 (지역별로 다양한 레이어를 추가할 수 있음)
#     folium.CircleMarker(location=center, radius=50, color="blue", fill=True).add_to(m)
#
#     return m._repr_html_()  # Dash에 HTML로 지도 전달

# import csv, os
# import folium
# import geopandas as gpd
# import shapely
# from folium.plugins import MarkerCluster
# import datetime
# from collections import Counter, defaultdict
# import dash
# from dash import dcc, html
# from dash.dependencies import Input, Output
# import plotly.express as px
# import pandas as pd
#
# f = csv.reader(open('input\\' + 'DRT정류장(통합).csv', 'r', encoding='cp949'))
# next(f)
#
# station_type = defaultdict(str)
#
# # 정류장 기존/가상 구분
# for row in f:
#     # print(row)
#
#     station_type[row[5]] = row[12]
#
# # print(station_type)
#
# # folium 지도
# m = folium.Map(location=[36.610167, 127.324325],
#                zoom_start=13,
#                width=1120,
#                height=800
#                )
#
# # os.path.join('input', 'filename')
#
# # 여러 개의 shp 파일을 불러와 지도에 추가하기
# shp_files = {"그린존": "input\\" + "청주_오송_그린존만.shp",
#              "레드존": "input\\" + "청주_오송_레드존.shp"
#              }
#
# for name, path in shp_files.items():
#     # GeoPandas로 shp 파일 읽기
#     gdf = gpd.read_file(path)
#
#     # 레드존 폴리곤 설정
#     if name == "레드존":
#
#         # 각 shp 파일을 GeoJson으로 추가
#         folium.GeoJson(
#             gdf,
#             name=name,  # 레이어 이름 설정
#             style_function=lambda x: {
#                 'fillColor': 'red',  # 폴리곤 색상
#                 'color': 'red',   # 경계선 색상
#                 'weight': 0.5,  # 경계선 두께
#                 'fillOpacity': 0.1  # 폴리곤 투명도 설정(0.5 = 50% 투명)
#             }
#         ).add_to(m)
#
#     # 그린존 폴리곤 설정
#     else:
#         # 각 shp 파일을 GeoJson으로 추가
#         folium.GeoJson(
#             gdf,
#             name=name,  # 레이어 이름 설정
#             style_function=lambda x: {
#                 'fillColor': 'green',  # 폴리곤 색상
#                 'color': 'green',  # 경계선 색상
#                 'weight': 0.5,  # 경계선 두께
#                 'fillOpacity': 0.1  # 폴리곤 투명도 설정(0.5 = 50% 투명)
#             }
#         ).add_to(m)
#
# # LayerControl을 추가하여 레이어를 제어할 수 있도록 설정
# folium.LayerControl().add_to(m)
#
# # 1. CSV 파일 불러오기 및 집계
# with open('input\\' + '02_driving_history_20241025233451.csv', newline='', encoding='cp949') as csvfile:
#     reader = csv.reader(csvfile)
#     next(reader)
#
#     # 정류장별 승차 및 하차량을 누적하기 위한 딕셔너리 초기화
#     in_count = defaultdict(int)
#     out_count = defaultdict(int)
#
#     for row in reader:
#         # print(row)
#         community = row[0]
#         service_nm = row[1]
#         rider_id = row[4]
#         adult = int(row[7])
#         teen = int(row[8])
#         children = int(row[9])
#         num = adult + teen + children
#         code = row[10]
#         # date = datetime.datetime(row[11].split('-')[0], row[11].split('-')[1], row[11].split('-')[2])
#         in_station = row[19]
#         out_station = row[20]
#         in_lon = float(row[23])
#         in_lat = float(row[24])
#         out_lon = float(row[25])
#         out_lat = float(row[26])
#
#         # 이용 완료 건만 분석
#         if code == '이용완료':
#
#             # 승차 정류장의 승차량 누적
#             in_count[(in_station, in_lat, in_lon)] += num
#
#             # 하차 정류장의 하차량 누적
#             out_count[(out_station, out_lat, out_lon)] += num
#
# for a in in_count:
#
#     lon = a[2]
#     lat = a[1]
#     nm = a[0]
#
#     # print(a)
#     # print(station_type[nm])
#
#     # 승차 및 하차량 정보 가져오기
#     num_in = in_count[a] if a in in_count else 0  # in_count에 값이 없을 때 0으로 설정
#     num_out = out_count[a] if a in out_count else 0  # out_count에 값이 없을 때 0으로 설정
#
#     # HTML로 팝업 내용을 구성
#     popup_text = f"<b>{nm}</b><br>승차 : {num_in}명, 하차 : {num_out}명"
#     popup = folium.Popup(popup_text, max_width=300)
#
#     # 정류장 유형에 따른 스타일 지정
#     if station_type[nm] == '가상정류장':
#         # 가상정류장: 빨간색 원으로 표시
#         folium.Circle(location=[lon, lat],
#                       popup=popup,
#                       radius=num_in * 10,
#                       color='red',
#                       fill=True,
#                       fill_color='red'
#                       ).add_to(m)
#     else:
#         # 기존정류장: 파란색 원으로 표시
#         folium.Circle(location=[lon, lat],
#                       popup=popup,
#                       radius=num_in * 10,
#                       color='blue',
#                       fill=True,
#                       fill_color='blue'
#                       ).add_to(m)
#
# m.save('map.html')
#
# # Initialize the Dash app
# app = dash.Dash(__name__)
#
# # Read the saved HTML file content for the folium map
# with open('map.html', 'r', encoding='utf-8') as f:
#     map_html = f.read()
#
# app.layout = html.Div([
#     # Display map and graphs based on selection
#     html.Div([
#         html.Div([html.Iframe(srcDoc=map_html, width='100%', height='600')],
#                  style={'width': '60%', 'display': 'inline-block'}),
#         html.Div([dcc.Graph(id='left-graph')], style={'width': '20%', 'display': 'inline-block'}),
#         html.Div([dcc.Graph(id='right-graph')], style={'width': '20%', 'display': 'inline-block'})
#     ])
# ])
#
# if __name__ == '__main__':
#     app.run_server(debug=True)