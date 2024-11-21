import os
import csv
import folium
import geopandas as gpd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from collections import defaultdict
import plotly.graph_objects as go
from folium import FeatureGroup
from datetime import datetime, timedelta
import logging
import functools
import holidays

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# 날짜 설정
day_now = (datetime.today() - timedelta(7)).strftime("%Y-%m-%d")

# 데이터 경로 설정
data_input_dir = os.path.join('input', '01 data')
shp_input_dir = os.path.join('input', '02 shp')
img_input_dir = os.path.join('assets')
station_file = os.path.join(data_input_dir, 'DRT정류장(통합).csv')
history_file = os.path.join(data_input_dir, 'DRT운행내역(통합).csv')
area_file = os.path.join(data_input_dir, '지역별 중심점.csv')

# 로그 추가: 데이터 파일 경로 확인
logging.info(f"Station file path: {station_file}")
logging.info(f"History file path: {history_file}")
logging.info(f"Area file path: {area_file}")

# 휴일 정보
kr_holidays = holidays.KR()

# 정류장 타입 구분 로드
def load_csv_data(file_path, encoding='cp949', has_header=True):
    data = []
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            reader = csv.reader(f)
            if has_header:
                next(reader)  # 헤더 건너뛰기
            data = list(reader)
        logging.info(f"Data from {file_path} loaded successfully.")
    except FileNotFoundError:
        logging.error(f"{file_path} 파일을 찾을 수 없습니다.")
    except Exception as e:
        logging.exception(f"Error reading {file_path}: {e}")
    return data

station_data = load_csv_data(station_file)
area_data = load_csv_data(area_file)
history_data = load_csv_data(history_file)

# 데이터 로드
station_type = defaultdict(str)
for row in station_data:
    station_type[row[5]] = row[12]

service_area = defaultdict(str)
area_center = defaultdict(list)
for row in area_data:
    service_area[row[0]] = row[1]
    area_center[row[0]] = [row[3], row[2]]

# CSV 파일을 읽어 지역별 집계
region_data = defaultdict(lambda: defaultdict(lambda: {
    "map_center": None,
    "shapefiles": {"그린존": "", "레드존": ""},
    "total_user": 0,
    "avg_wait_time": [],
    "stations": defaultdict(lambda: {"승차": 0, "하차": 0}),
    "od": defaultdict(int),
    "operation_type": defaultdict(int),
    "user_type": {"성인": 0, "청소년": 0, "어린이": 0},
    "call_type": defaultdict(int),
    "time_wait": {hour: [] for hour in range(6, 22)},
    "time_users": {hour: 0 for hour in range(6, 22)},
    "wait_dist": {**{(f"{5 * i}분 미만" if i == 1 else f"{5 * (i - 1)}~{5 * i}분"): [] for i in range(1, 13)},
                  "60분 이상": []},   # ** 딕셔너리 언패킹 : 두 개의 딕셔너리를 합쳐 새로운 딕셔너리 생성
    "time_travel": {hour: [] for hour in range(6, 22)},
}))

for row in history_data:
    area = row[0]
    total_ride = int(row[6])
    adult_num = int(row[7])
    teen_num = int(row[8])
    children_num = int(row[9])
    total_num = int(row[7]) + int(row[8]) + int(row[9])
    date = row[11]
    operation_type = row[10]
    call_type = row[12].split("(")[0]
    in_time = int(row[15].split(':')[0]) if row[15] else None
    waiting_time = sum(int(x) * [1/60, 1, 60][i] for i, x in enumerate(reversed(row[17].split(':')))) if row[17] else None
    travel_time = sum(int(x) * [1/60, 1, 60][i] for i, x in enumerate(reversed(row[18].split(':')))) if row[18] else None
    o_lat = float(row[23])
    o_lon = float(row[24])
    d_lat = float(row[25])
    d_lon = float(row[26])
    o_station = row[19], o_lat, o_lon
    d_station = row[20], d_lat, d_lon
    o_d = row[19] + "-" + row[20]

    # 필요 시 초기화
    if not region_data[service_area[area]][date]["map_center"]:
        region_data[service_area[area]][date]["map_center"] = area_center[area]
        region_data[service_area[area]][date]["shapefiles"]["그린존"] = os.path.join(shp_input_dir, f"{service_area[area]}_그린존만.shp")
        region_data[service_area[area]][date]["shapefiles"]["레드존"] = os.path.join(shp_input_dir, f"{service_area[area]}_레드존.shp")

    # 배차 분류 집계
    region_data[service_area[area]][date]["operation_type"][operation_type] += 1

    # 호출 방법 집계
    region_data[service_area[area]][date]["call_type"][call_type] += 1

    # 이용 완료 건에 대한 집계
    if operation_type == '이용완료':
        region_data[service_area[area]][date]["total_user"] += total_num    # 이용인원 집계
        region_data[service_area[area]][date]["avg_wait_time"] += [waiting_time]     # 평균 대기시간 집계
        region_data[service_area[area]][date]["user_type"]["성인"] += adult_num   # 이용자 유형(성인) 집계
        region_data[service_area[area]][date]["user_type"]["청소년"] += teen_num   # 이용자 유형(청소년) 집계
        region_data[service_area[area]][date]["user_type"]["어린이"] += children_num   # 이용자 유형(어린이) 집계
        region_data[service_area[area]][date]["time_wait"][in_time] += [waiting_time]    # 시간대별 대기시간 집계
        region_data[service_area[area]][date]["time_users"][in_time] += total_num   # 시간대별 이용인원 집계
        region_data[service_area[area]][date]["time_travel"][in_time] += [travel_time]  # 시간대별 이동시간 집계

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

        # 통행 OD 초기화 및 집계
        if o_d not in region_data[service_area[area]][date]["od"]:
            region_data[service_area[area]][date]["od"][o_d] = 0
        region_data[service_area[area]][date]["od"][o_d] += total_num

holiday_data = defaultdict(lambda: {
    "users_list": {"평일": [], "휴일": []},
    "calls_list": {"평일": [], "휴일": []}
})

for service_a, services in region_data.items():
    for service_d, data in services.items():
        users = data["total_user"]
        calls = sum(data["call_type"].values())

        if service_d in kr_holidays:
            holiday_data[service_a]["users_list"]["휴일"] += [users]
            holiday_data[service_a]["calls_list"]["휴일"] += [calls]
        else:
            holiday_data[service_a]["users_list"]["평일"] += [users]
            holiday_data[service_a]["calls_list"]["평일"] += [calls]

# print(holiday_data)

logging.info("Completed reading history data.")

# Dash
app = dash.Dash(__name__)
server = app.server  # gunicorn은 server 객체를 사용함
app.scripts.config.serve_locally = True
app.css.config.serve_locally = True

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
            style={'width': '30%'}
        ),

        # 상단 - 우측 기준 일자 DatePicker
        dcc.DatePickerSingle(
            id='date-picker',
            date=day_now,
            display_format='YYYY-MM-DD',
            style={'width': '30%'}
        ),

        # 호출 건수
        html.Div([
                # 이미지 삽입
                html.Img(
                    src=os.path.join(img_input_dir, 'call_icon.png'),  # 이미지 경로 또는 URL
                    style={'height': '50px', 'margin-right': '10px'}
                ),
                # 총 호출건수 표시
                html.Div([
                    html.Span(id='total-calls-display', children='000건',
                              style={'font-size': '26px', 'font-weight': 'bold'}),
                    html.Br(),  # 줄바꿈
                    html.Div(id='avg-calls-display', children='(평일)000건/(휴일)000건',
                             style={'font-size': '13px', 'color': 'gray'})
                ], style={'display': 'inline-block', 'vertical-align': 'top'})
            ], style={
                'display': 'flex',
                'align-items': 'center',    # 세로 방향 가운데 정렬
                'border': '1px solid lightgray',
                'padding': '10px',
                'width': '250px',  # 원하는 크기로 조정
                'box-sizing': 'border-box'
            }),

        # 이용 인원
        html.Div([
                # 이미지 삽입
                html.Img(
                    src=os.path.join(img_input_dir, 'users_icon.png'),  # 이미지 경로 또는 URL
                    style={'height': '50px', 'margin-right': '10px'}
                ),
                # 총 이용인원 표시
                html.Div([
                    html.Span(id='total-users-display', children='000명',
                              style={'font-size': '26px', 'font-weight': 'bold'}),
                    html.Br(),  # 줄바꿈
                    html.Div(id='avg-users-display', children='(평일)000명/(휴일)000명',
                             style={'font-size': '13px', 'color': 'gray'})
                ], style={'display': 'inline-block', 'vertical-align': 'top'})
            ], style={
                'display': 'flex',
                'align-items': 'center',    # 세로 방향 가운데 정렬
                'border': '1px solid lightgray',
                'padding': '10px',
                'width': '250px',  # 원하는 크기로 조정
                'box-sizing': 'border-box'
            })
    ], style={'display': 'flex', 'align-items': 'center', 'padding': '10px', 'gap': '10px'}),

    # 지도와 파이 차트를 포함하는 중간 부분
    html.Div([
        # 왼쪽 - 지도
        html.Div([
            html.Iframe(id="map", width="100%", height="96%")
        ], style={'width': '40%', 'height': '600px', 'display': 'inline-block', 'padding': '10px',
                  'border': '1px solid lightgray'}),

        # 오른쪽 - 이용량 마크 3개, 차트 3개
        html.Div([
            # 상위 5개소 3개
            html.Div([
                html.Div(dcc.Markdown(id="in-top5", style={'font-size': '14px', 'margin': '10px'}),
                         style={'flex': '1', 'height': '100%', 'display': 'inline-block',
                                'padding': '1px', 'border': '1px solid lightgray'}),  # 승차량 상위5개소
                html.Div(dcc.Markdown(id="out-top5", style={'font-size': '14px', 'margin': '10px'}),
                         style={'flex': '1', 'height': '100%', 'display': 'inline-block',
                                'padding': '1px', 'border': '1px solid lightgray'}),  # 하차량 상위5개소
                html.Div(dcc.Markdown(id="od-top5", style={'font-size': '14px', 'margin': '10px'}),
                         style={'flex': '1', 'height': '100%', 'display': 'inline-block',
                                'padding': '1px', 'border': '1px solid lightgray'}),  # 통행 상위5개소
            ], style={'display': 'flex', 'flex-wrap': 'flex', 'width': '100%', 'height': '50%'}),

            # 파이 차트 3개
            html.Div([
                html.Div(dcc.Graph(id="ride-pie-chart"),
                         style={'flex': '1', 'height': '100%', 'display': 'inline-block',
                                'padding': '1px', 'border': '1px solid lightgray'}),  # 배차 분류
                html.Div(dcc.Graph(id="call-pie-chart"),
                         style={'flex': '1', 'height': '100%', 'display': 'inline-block',
                                'padding': '1px', 'border': '1px solid lightgray'}),  # 이용자 유형
                html.Div(dcc.Graph(id="user-pie-chart"),
                         style={'flex': '1', 'height': '100%', 'display': 'inline-block',
                                'padding': '1px', 'border': '1px solid lightgray'})  # 호출 방법
            ], style={'display': 'flex', 'flex-wrap': 'flex', 'width': '100%', 'height': '50%'})
        ], style={'width': '60%', 'height': '600px', 'display': 'inline-block'})
    ], style={'display': 'flex', 'width': '100%', 'height': '600px'}),

    # 하단 - 시간대별 대기시간 및 이동시간 그래프
    html.Div([
        html.Div([dcc.Graph(id="waiting-time-chart")],
                 style={'width': '50%', 'height': '250px', 'display': 'inline-block', 'padding': '10px',
                        'border': '1px solid lightgray'}),
        html.Div([dcc.Graph(id="waiting-time-dist")],
                 style={'width': '50%', 'height': '250px', 'display': 'inline-block', 'padding': '10px',
                        'border': '1px solid lightgray'})
    ], style={'display': 'flex', 'width': '100%'})
])  # 레이아웃의 끝부분에 괄호를 추가해줌

# 콜백 함수: '총 호출건수' 텍스트 업데이트
@app.callback(
    Output('total-calls-display', 'children'),
    [Input('region-dropdown', 'value'),
    Input('date-picker', 'date')]
)
def update_total_users(selected_region, selected_date):
    region_info = region_data[selected_region][selected_date]
    total_calls = sum(region_info["call_type"].values())

    return [html.B(f'{total_calls}건')]

# 콜백 함수: '지역별 평균 호출건수, 이용인원' 텍스트 업데이트
@app.callback(
    [Output('avg-users-display', 'children'),
     Output('avg-calls-display', 'children')],
    Input('region-dropdown', 'value')
)

def update_area_avg(selected_region):
    avg_users = holiday_data[selected_region]["users_list"]
    avg_calls = holiday_data[selected_region]["calls_list"]

    avg_users_weekday = int(round(sum(avg_users["평일"]) / len(avg_users["평일"]), 0))
    avg_users_holiday = int(round(sum(avg_users["휴일"]) / len(avg_users["휴일"]), 0))
    avg_calls_weekday = int(round(sum(avg_calls["평일"]) / len(avg_calls["평일"]), 0))
    avg_calls_holiday = int(round(sum(avg_calls["휴일"]) / len(avg_calls["휴일"]), 0))

    # '(평일) 000건 / (휴일) 000건
    avg_users_text = f"(평일){avg_users_weekday}명/(주말){avg_users_holiday}명"
    avg_calls_text = f"(평일){avg_calls_weekday}건/(주말){avg_calls_holiday}건"

    return avg_users_text, avg_calls_text

# 콜백 함수: '총 이용인원' 텍스트 업데이트
@app.callback(
    Output('total-users-display', 'children'),
    [Input('region-dropdown', 'value'),
    Input('date-picker', 'date')]
)
def update_total_users(selected_region, selected_date):
    region_info = region_data[selected_region][selected_date]
    total_users = region_info["total_user"]

    return [html.B(f'{total_users}명')]

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

            # functools.partial 사용
            style_function = functools.partial(
                lambda x, color: {
                    'fillColor': color,
                    'color': color,
                    'weight': 1,
                    'fillOpacity': 0.1
                },
                color=color
            )

            folium.GeoJson(
                gdf,
                name=name,
                style_function=style_function
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

# 승차, 하차, 통행OD 상위 5개소 업데이트
@app.callback(
    [Output("in-top5", "children"),
     Output("out-top5", "children"),
     Output("od-top5", "children")],
    [Input("region-dropdown", "value"),
     Input("date-picker", "date")]
)
def update_pie_charts(selected_region, selected_date):
    region_info = region_data[selected_region][selected_date]

    # 승차 기준 상위 5개 정류장
    top5_in = sorted(region_info["stations"].items(), key=lambda item: item[1]['승차'], reverse=True)[:5]
    in_text = "### 승차량 상위 5개 정류장\n"
    for i, station in enumerate(top5_in, start=1):
        station_name = station[0][0]  # 정류장명 (튜플의 첫 번째 요소)
        station_name = str(station_name).replace('[', '\\[').replace(']', '\\]')  # 대괄호 이스케이프 처리
        station_data = station[1]  # Station data
        in_text += f"{i}. **{station_name}** : {station_data['승차']}명\n"
        in_text += "\n"

    # 하차 기준 상위 5개 정류장
    top5_out = sorted(region_info["stations"].items(), key=lambda item: item[1]['하차'], reverse=True)[:5]
    out_text = "### 하차량 상위 5개 정류장\n"
    for i, station in enumerate(top5_out, start=1):
        station_name = station[0][0]  # 정류장명 (튜플의 첫 번째 요소)
        station_name = str(station_name).replace('[', '\\[').replace(']', '\\]')  # 대괄호 이스케이프 처리
        station_data = station[1]  # Station data
        out_text += f"{i}. **{station_name}** : {station_data['하차']}명\n"
        out_text += "\n"

    # 기점-종점 기준 상위 5개 정류장
    top5_od = sorted(region_info["od"].items(), key=lambda x: x[1], reverse=True)[:5]
    od_text = "### 통행량 상위 5개 O-D\n"
    for i, od_station in enumerate(top5_od, start=1):
        o = (od_station[0].split('-')[0]).replace('[', '\\[').replace(']', '\\]')  # 대괄호 이스케이프 처리
        d = (od_station[0].split('-')[1]).replace('[', '\\[').replace(']', '\\]')  # 대괄호 이스케이프 처리

        od_text += f"{i}. **{o + '-' + d}** : {od_station[1]}명\n"
        od_text += "\n"

    return in_text, out_text, od_text

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
        fig = go.Figure(go.Pie(
            labels=labels, values=values, textinfo="percent+value", hoverinfo="label+percent+value", hole=0.5,
            texttemplate='%{value}<br>(<b>%{percent:.2f})</b>'
        ))
        fig.update_layout(
            title=title, width=330, height=250, margin=dict(t=100, b=0, l=10, r=10), paper_bgcolor='rgba(0, 0, 0, 0)')
        pie_charts.append(fig)

    return pie_charts

# 지역에 따른 시간대별 현황 그래프 업데이트
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

    times2 = list(region_info["time_travel"].keys())
    avg_travel_times = [
        round(sum(travel_times) / len(travel_times) if travel_times else 0, 1)
        for travel_times in region_info["time_travel"].values()
    ]

    # 그래프 생성
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=avg_waiting_times, name="대기시간", mode='lines+markers'))
    fig.add_trace(go.Scatter(x=times, y=avg_travel_times, name="이동시간", mode='lines+markers'))
    fig.add_trace(go.Scatter(x=times, y=user_counts, name="이용인원", mode='lines+markers', yaxis="y2"))

    # 그래스 스타일 수정
    fig.update_layout(
        title="시간대별 현황",
        xaxis=dict(title="시간대", range=[5, 22]),
        yaxis=dict(title="대기시간 및 이동시간(분)", side='left',
                   range=[0, max(max(avg_waiting_times), max(avg_travel_times)) * 1.2]),
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

# 지역에 따른 대기시간 분포 그래프 업데이트
@app.callback(
    Output("waiting-time-dist", "figure"),
    [Input("region-dropdown", "value"),
     Input("date-picker", "date")]
)
def update_waiting_time_chart(selected_region, selected_date):
    region_info = region_data[selected_region][selected_date]

    # 대기시간 리스트 불러오기
    labels = list(region_info["wait_dist"].keys())
    sizes = [
        len(times) if len(times) > 0 else 0  # 구간별 평균 대기 시간 계산
        for times in region_info["wait_dist"].values()
    ]
    # 각 값의 비율 계산
    total = sum(sizes)
    percentages = [round((size / total) * 100, 1) for size in sizes]    # 비율 계산 (백분율)

    # 바 차트 생성
    fig = go.Figure(data=[
        go.Bar(x=labels, y=percentages)  # y에 비율 값을 사용
    ])

    # 그래프 레이아웃 설정
    fig.update_layout(
        title="대기시간 분포",
        xaxis=dict(title="대기시간(분)"),
        yaxis=dict(title="비율(%)", range=[0, max(percentages) * 1.2]),
        width=900, height=250,
        bargap=0.2,  # 막대 사이 간격
        plot_bgcolor='whitesmoke',  # 플롯 배경색
        paper_bgcolor='white',  # 그래프 전체 배경색
        margin=dict(l=15, r=15, t=50, b=20),  # 여백 설정
        hovermode='x unified',  # 호버 스타일
    )

    return fig

# 앱 실행
if __name__ == '__main__':
    app.run_server(debug=True)
