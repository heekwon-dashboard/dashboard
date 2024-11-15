import os
import csv
import folium
import geopandas as gpd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from collections import defaultdict
import plotly.express as px
from datetime import datetime, timedelta
import plotly.graph_objects as go
from folium import FeatureGroup
from collections import Counter

# 날짜 설정
day_now = (datetime.today() - timedelta(1)).strftime("%Y-%m-%d")

# 데이터 경로 설정
data_input_dir = 'input\\01 data'
shp_input_dir = 'input\\02 shp'
station_file = os.path.join(data_input_dir, 'DRT정류장(통합).csv')
history_file = os.path.join(data_input_dir, 'DRT운행내역(통합).csv')
area_file = os.path.join(data_input_dir, '지역별 중심점.csv')

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

# 서비스지역 구분
service_area = defaultdict(str)
area_center = defaultdict(list)
try:
    with open(area_file, 'r', encoding='cp949') as f:
        reader = csv.reader(f)
        next(reader)  # 헤더 건너뛰기
        for row in reader:
            # print(row)
            service_area[row[0]] = row[1]
            area_center[row[0]] = [row[3], row[2]]

    # print(service_area)
    # print(area_center)

except FileNotFoundError:
    print(f"Error: {station_file} 파일을 찾을 수 없습니다.")
except Exception as e:
    print(f"Error: {e}")

# CSV 파일을 읽어 지역별 집계
region_data = defaultdict()

try:
    with open(history_file, newline='', encoding='cp949') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # 헤더 건너뛰기

        for row in reader:
            # print(row)

            # 변수 정의
            area = row[0]
            total_ride = int(row[6])
            adult_num = int(row[7])
            teen_num = int(row[8])
            children_num = int(row[9])
            total_num = int(row[7]) + int(row[8]) + int(row[9])
            operation_type = row[10]
            date = row[11]
            call_type = row[12]
            call_time = int(row[14].split(':')[0]) # 시간 단위
            in_time = int(row[15].split(':')[0]) if row[15] != '' else None     # 시간 단위
            out_time = int(row[16].split(':')[0]) if row[16] != '' else None    # 시간 단위
            waiting_time = int(row[17].split(':')[0]) * 60 + int(row[17].split(':')[1]) + int(row[17].split(':')[2]) / 60 if row[17] != '' else None # 분 단위
            travel_time = int(row[18].split(':')[0]) * 60 + int(row[18].split(':')[1]) + int(row[18].split(':')[2]) / 60 if row[18] != '' else None # 분 단위
            o_lat = float(row[23])
            o_lon = float(row[24])
            d_lat = float(row[25])
            d_lon = float(row[26])
            o_station = row[19], o_lat, o_lon
            d_station = row[20], d_lat, d_lon

            # 지역 데이터가 이미 존재하지 않는 경우 초기화
            if service_area[area] not in region_data:
                region_data[service_area[area]] = {}

            if date not in region_data[service_area[area]]:
                region_data[service_area[area]][date] = {}

                # 중심점
                region_data[service_area[area]][date]["map_center"] = [area_center[area][0], area_center[area][1]]

                # shp 파일
                region_data[service_area[area]][date]["shapefiles"] = {
                    "그린존": os.path.join(shp_input_dir, f"{service_area[area]}_그린존만.shp"),
                    "레드존": os.path.join(shp_input_dir, f"{service_area[area]}_레드존.shp")
                }

                # 정류장 현황 초기화
                region_data[service_area[area]][date]["stations"] = {}

                # 배차 분류 현황 초기화
                region_data[service_area[area]][date]["operation_type"] = defaultdict(int) # {"이용완료": 0, "호출취소": 0, "노쇼": 0}

                # 이용자 유형 현황 초기화
                region_data[service_area[area]][date]["user_type"] = {"성인": 0, "청소년": 0, "어린이": 0}

                # 호출 방법 현황 초기화
                region_data[service_area[area]][date]["call_type"] = defaultdict(int) # {"앱(실시간)": 0, "전화(실시간)": 0, "호출벨(실시간)": 0}

                # 시간대별 대기시간 현황 초기화
                region_data[service_area[area]][date]["time_wait"] = {6: [], 7: [], 8: [], 9: [], 10: [], 11: [],
                                                                      12: [], 13: [], 14: [], 15: [], 16: [], 17: [],
                                                                      18: [], 19: [], 20: [], 21: []}

                # 시간대별 이용인원 현황 초기화
                region_data[service_area[area]][date]["time_users"] = {6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0,
                                                                       13: 0, 14: 0, 15: 0, 16: 0, 17: 0, 18: 0, 19: 0,
                                                                       20: 0, 21: 0}

                # 대기시간 분포 초기화
                region_data[service_area[area]][date]["wait_dist"] = {"5분 미만": [], "5~10분": [], "10~15분": [],
                                                                      "15~20분": [], "20~25분": [], "25~30분": [],
                                                                      "30~35분": [], "35~40분": [], "40~45분": [],
                                                                      "45~50분": [], "50~55분": [], "55~60분": [],
                                                                      "60분 이상": []}

                # # 시간대별 이동시간 현황 초기화
                # region_data[service_area[area]][date]["time_travel"] = {6: [], 7: [], 8: [], 9: [], 10: [], 11: [],
                #                                                         12: [], 13: [], 14: [], 15: [], 16: [], 17: [],
                #                                                         18: [], 19: [], 20: [], 21: []}

            # 정류장 현황 초기화
            if o_station not in region_data[service_area[area]][date]["stations"]:
                region_data[service_area[area]][date]["stations"][o_station] = {"승차": 0, "하차": 0}

            if d_station not in region_data[service_area[area]][date]["stations"]:
                region_data[service_area[area]][date]["stations"][d_station] = {"승차": 0, "하차": 0}

            # 배차 분류 집계
            region_data[service_area[area]][date]["operation_type"][operation_type] += 1

            # 호출 방법 집계
            region_data[service_area[area]][date]["call_type"][call_type] += 1

            # 이용 완료 건에 대한 집계
            if operation_type == '이용완료':

                # 이용자 유형 집계
                region_data[service_area[area]][date]["user_type"]["성인"] += adult_num
                region_data[service_area[area]][date]["user_type"]["청소년"] += teen_num
                region_data[service_area[area]][date]["user_type"]["어린이"] += children_num

                # 시간대별 대기시간 집계
                region_data[service_area[area]][date]["time_wait"][in_time] += [waiting_time]

                # 시간대별 이용인원 집계
                region_data[service_area[area]][date]["time_users"][in_time] += total_num

                # 정류장 승하차 집계
                region_data[service_area[area]][date]["stations"][o_station]["승차"] += total_num
                region_data[service_area[area]][date]["stations"][d_station]["하차"] += total_num

                # 대기시간 분포 집계
                if waiting_time < 5:
                    region_data[service_area[area]][date]["wait_dist"]["5분 미만"] += [waiting_time]
                elif waiting_time < 10:
                    region_data[service_area[area]][date]["wait_dist"]["5~10분"] += [waiting_time]
                elif waiting_time < 15:
                    region_data[service_area[area]][date]["wait_dist"]["10~15분"] += [waiting_time]
                elif waiting_time < 20:
                    region_data[service_area[area]][date]["wait_dist"]["15~20분"] += [waiting_time]
                elif waiting_time < 25:
                    region_data[service_area[area]][date]["wait_dist"]["20~25분"] += [waiting_time]
                elif waiting_time < 30:
                    region_data[service_area[area]][date]["wait_dist"]["25~30분"] += [waiting_time]
                elif waiting_time < 35:
                    region_data[service_area[area]][date]["wait_dist"]["30~35분"] += [waiting_time]
                elif waiting_time < 40:
                    region_data[service_area[area]][date]["wait_dist"]["35~40분"] += [waiting_time]
                elif waiting_time < 45:
                    region_data[service_area[area]][date]["wait_dist"]["40~45분"] += [waiting_time]
                elif waiting_time < 50:
                    region_data[service_area[area]][date]["wait_dist"]["45~50분"] += [waiting_time]
                elif waiting_time < 55:
                    region_data[service_area[area]][date]["wait_dist"]["50~55분"] += [waiting_time]
                elif waiting_time < 60:
                    region_data[service_area[area]][date]["wait_dist"]["55~60분"] += [waiting_time]
                else:
                    region_data[service_area[area]][date]["wait_dist"]["60분 이상"] += [waiting_time]

# # 시간대별 이동시간 집계
                # region_data[service_area[area]][date]["time_travel"][in_time] += [travel_time]

        # print(day_now)
        # print(region_data)

except FileNotFoundError:
    print(f"Error: {history_file} 파일을 찾을 수 없습니다.")
except Exception as e:
    print(f"Error: {e}")

app = dash.Dash(__name__)

# Dash 레이아웃 설정

app.layout = html.Div([
    # 상단 - 지역 선택 Dropdown
    html.Div([
        dcc.Dropdown(
            id='region-dropdown',
            options=[{'label': '청주_오송', 'value': '청주_오송'},
                     {'label': '청주_남이', 'value': '청주_남이'},
                     {'label': '청주_가덕문의', 'value': '청주_가덕문의'},
                     {'label': '청주_내수북이', 'value': '청주_내수북이'},
                     {'label': '청주_미원낭성', 'value': '청주_미원낭성'},
                     {'label': '청주_오창', 'value': '청주_오창'},
                     {'label': '청주_옥산', 'value': '청주_옥산'},
                     {'label': '청주_현도', 'value': '청주_현도'},
                     {'label': '청주_강내', 'value': '청주_강내'}],
            value='청주_오송',
            style={'width': '80%'}
        )
    ], style={'width': '25%', 'display': 'inline-block', 'vertical-align': 'top', 'padding': '10px'}),

    # 상단 - 우측 기준 일자 DatePicker
        html.Div([
            dcc.DatePickerSingle(
                id='date-picker',
                date=(datetime.today() - timedelta(1)).strftime("%Y-%m-%d"),  # 초기 선택 날짜 (예시)
                display_format='YYYY-MM-DD',
                style={'width': '80%'}
            )
        ], style={'width': '25%', 'display': 'inline-block', 'vertical-align': 'top', 'padding': '10px', 'text-align': 'right'}),


    # 지도와 파이 차트를 포함하는 중간 부분
    html.Div([
        # 왼쪽 - 지도
        html.Div([
            html.Iframe(id="map", width="100%", height="100%")
        ], style={'width': '50%', 'height': '600px', 'display': 'inline-block', 'padding': '10px',
                  'border': '1px solid lightgray'}),

        # 오른쪽 - 파이 차트 4개
        html.Div([
            html.Div(dcc.Graph(id="ride-pie-chart"),
                     style={'width': '48%', 'height': '305px', 'display': 'inline-block',
                            'padding': '1px', 'border': '1px solid lightgray'}),  # 배차 분류
            html.Div(dcc.Graph(id="call-pie-chart"),
                     style={'width': '48%', 'height': '305px', 'display': 'inline-block',
                            'padding': '1px', 'border': '1px solid lightgray'}),  # 이용자 유형
            html.Div(dcc.Graph(id="user-pie-chart"),
                     style={'width': '48%', 'height': '305px', 'display': 'inline-block',
                            'padding': '1px', 'border': '1px solid lightgray'}),  # 호출 방법
            html.Div(dcc.Graph(id="another-pie-chart"),
                     style={'width': '48%', 'height': '305px', 'display': 'inline-block',
                            'padding': '1px', 'border': '1px solid lightgray'})   # 추가적인 파이 차트 예시
        ], style={'display': 'flex', 'flex-wrap': 'wrap', 'width': '50%'})
    ], style={'display': 'flex', 'width': '100%'}),

    # 하단 - 시간대별 대기시간 및 이동시간 그래프
    html.Div([
        html.Div([dcc.Graph(id="waiting-time-chart")],
                 style={'width': '50%', 'height': '250px', 'display': 'inline-block', 'padding': '1px',
                        'border': '1px solid lightgray'}),
        html.Div([dcc.Graph(id="waiting-time-dist")],
                 style={'width': '50%', 'height': '250px', 'display': 'inline-block', 'padding': '1px',
                        'border': '1px solid lightgray'})
    ], style={'display': 'flex', 'width': '100%'})
])

# 지역에 따른 지도 업데이트
@app.callback(
    Output("map", "srcDoc"),
    [Input("region-dropdown", "value"),
     Input("date-picker", "date")]
)
def update_map(selected_region, selected_date):
    region_info = region_data[selected_region][selected_date]
    m = folium.Map(location=region_info["map_center"], zoom_start=12, tiles="cartodbpositron")

    # 범례 그룹 추가
    red_zone = FeatureGroup(name='레드존', show=True).add_to(m)
    green_zone = FeatureGroup(name='그린존', show=True).add_to(m)

    # 지역의 shapefiles 추가
    for name, path in region_info["shapefiles"].items():
        try:
            gdf = gpd.read_file(path)
            color = 'red' if name == "레드존" else 'green'
            feature_group = red_zone if color == 'red' else green_zone
            folium.GeoJson(
                gdf,
                name=name,
                style_function=lambda x, color=color: {
                    'fillColor': color,
                    'color': color,
                    'weight': 1,
                    'fillOpacity': 0.1
                }
            ).add_to(feature_group)
        except FileNotFoundError:
            print(f"Error: {path} 파일을 찾을 수 없습니다.")
        except Exception as e:
            print(f"Error: {e}")

    # 범례 그룹 추가
    existing_stations_group = FeatureGroup(name="기존정류장", show=True).add_to(m)
    virtual_stations_group = FeatureGroup(name="가상정류장", show=True).add_to(m)

    # 정류장 정보 추가
    for station, count in region_info["stations"].items():
        popup_text = f"<b>{station[0]}</b><br>승차 : {count['승차']}명, " \
                     f"하차 : {count['하차']}명"
        color = 'red' if station_type[station[0]] == '가상정류장' else 'blue'

        # 정류장의 FeatureGroup에 추가
        target_group = virtual_stations_group if color == 'red' else existing_stations_group

        # 이용내역이 없는 경우
        folium.Circle(
            location=[station[1], station[2]],
            popup=folium.Popup(popup_text, max_width=300),
            radius=(count['승차'] + count['하차']) * 10, # 정류장 표시 위해
            color=color,
            fill=True,
            fill_color=color,

        ).add_to(target_group)

    # LayerControl을 추가하여 레이어를 제어할 수 있도록 설정
    folium.LayerControl(collapsed=False).add_to(m)

    # 지도 저장 및 HTML 반환
    map_file = 'temp_map.html'
    m.save(map_file)
    with open(map_file, 'r', encoding='utf-8') as f:
        return f.read()

# 공통 파이 차트 업데이트 함수
@app.callback(
    [Output("ride-pie-chart", "figure"),
     Output("user-pie-chart", "figure"),
     Output("call-pie-chart", "figure")],
    [Input("region-dropdown", "value"),
     Input("date-picker", "date")]
)
def update_pie_charts(selected_region, selected_date):
    region_info = region_data[selected_region][selected_date]
    pie_charts = []

    for key, title in zip(
            ["operation_type", "user_type", "call_type"],
            ["호출 현황", "이용자 현황", "호출 방법"]
    ):
        labels = list(region_info[key].keys())
        values = list(region_info[key].values())
        fig = go.Figure(go.Pie(labels=labels, values=values, textinfo="percent+value"))
        fig.update_layout(title=title, width=425, height=300)
        pie_charts.append(fig)

    return pie_charts

# 지역에 따른 시간대별 대기시간 그래프 업데이트
@app.callback(
    Output("waiting-time-chart", "figure"),
    [Input("region-dropdown", "value"),
     Input("date-picker", "date")]
)
def update_waiting_time_chart(selected_region, selected_date):
    region_info = region_data[selected_region][selected_date]
    times = list(region_info["time_wait"].keys())
    avg_waiting_times = [
        round(sum(wait_times) / len(wait_times) if wait_times else 0, 1)
        for wait_times in region_info["time_wait"].values()
    ]
    user_counts = list(region_info["time_users"].values())

    # 그래프 생성
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=avg_waiting_times, name="대기시간", mode='lines+markers'))
    fig.add_trace(go.Scatter(x=times, y=user_counts, name="이용인원", mode='lines+markers', yaxis="y2"))

    # 그래스 스타일 수정
    fig.update_layout(
        title="시간대별 평균 대기시간 및 이용인원",
        xaxis=dict(title="시간대", range=[5, 22]),
        yaxis=dict(title="평균 대기시간(분)", range=[0, max(avg_waiting_times) * 1.2]),
        yaxis2=dict(title="이용인원(인)", overlaying='y', side='right', range=[0, max(user_counts) * 1.2]),
        width=900, height=250,
        plot_bgcolor='whitesmoke',  # 플롯 배경색
        paper_bgcolor='white',  # 그래프 전체 배경색
        margin=dict(l=15, r=15, t=50, b=20),  # 여백 설정
        hovermode='x unified',  # 호버 스타일

        # 범례 위치 조정
        legend=dict(
            x=1.1,                  # x 좌표를 1보다 크게 설정하여 오른쪽으로 이동
            y=1,                    # y 좌표를 1로 설정하여 상단에 고정
            bordercolor="black",    # 테두리 색상 설정
            borderwidth=1,           # 테두리 두께 설정
        )
    )

    return fig

# 지역에 따른 시간대별 이동시간 그래프 업데이트
@app.callback(
    Output("waiting-time-dist", "figure"),
    [Input("region-dropdown", "value"),
     Input("date-picker", "date")]
)
def update_waiting_time_chart(selected_region, selected_date):
    region_info = region_data[selected_region][selected_date]

    # 대기시간 리스트 불러오기
    times = list(region_info["time_travel"].keys())
    avg_travel_times = [
        round(sum(travel_times) / len(travel_times) if travel_times else 0, 1)
        for travel_times in region_info["time_travel"].values()
    ]
#
#     # 평균 이동시간으로 그래프 생성
#     fig = px.line(
#         x=times,
#         y=avg_travel_times,
#         title="시간대별 평균 이동시간(분)",
#         labels={"x": "시간대", "y": "평균 이동시간(분)"}
#     )
#
#     # 그래프 스타일 조정
#     fig.update_traces(
#         line=dict(color='royalblue', width=3, dash='solid'),  # 라인 색상과 스타일
#         marker=dict(size=8, symbol='circle', color='blue', line=dict(color='black', width=1))  # 마커 스타일
#     )
#
#     fig.update_layout(width=900, height=250,
#                       title=dict(text="시간대별 평균 이동시간(분)", font=dict(size=15, color='black')),
#                       xaxis=dict(
#                           tickmode='linear', title="시간대", titlefont=dict(size=10),
#                           tickfont=dict(size=10), showgrid=True, gridcolor='lightgrey',
#                           range=[5, 22]
#                       ),
#                       yaxis=dict(
#                           title="평균 이동시간(분)", titlefont=dict(size=10),
#                           tickfont=dict(size=14), showgrid=True, gridcolor='lightgrey',
#                           range=[0, max(avg_travel_times) * 1.2]
#                       ),
#                       plot_bgcolor='whitesmoke',  # 플롯 배경색
#                       paper_bgcolor='white',  # 그래프 전체 배경색
#                       margin=dict(l=15, r=15, t=50, b=20),  # 여백 설정
#                       hovermode='x unified'  # 호버 스타일
#     )
#
#     return fig

# 앱 실행
if __name__ == '__main__':
    app.run_server(debug=True)