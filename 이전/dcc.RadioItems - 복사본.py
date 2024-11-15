# 필요한 라이브러리 임포트
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd

# 샘플 데이터 생성
data = pd.DataFrame({
    '지역': ['서울', '서울', '부산', '부산', '대구', '대구'],
    '날짜': pd.to_datetime(['2024-11-01', '2024-11-02', '2024-11-01', '2024-11-02', '2024-11-01', '2024-11-02']),
    '호출 건수': [100, 150, 120, 130, 110, 140],
    '이용 인원': [90, 130, 110, 120, 100, 135],
    '운행 대수': [10, 15, 12, 13, 11, 14]
})

# 대시보드 앱 초기화
app = dash.Dash(__name__)

# 레이아웃 정의
app.layout = html.Div([
    html.H1("지역 및 날짜 선택에 따른 데이터 조회", style={'textAlign': 'center'}),

    html.Div([
        html.Label("지역 선택:"),
        dcc.Dropdown(
            id='region-dropdown',
            options=[{'label': region, 'value': region} for region in data['지역'].unique()],
            value='서울',
            clearable=False
        ),
        html.Label("날짜 선택:"),
        dcc.DatePickerSingle(
            id='date-picker',
            date=data['날짜'].min().date(),
        )
    ], style={'marginBottom': '20px'}),

    html.Div(id='output-container', style={'fontSize': '20px', 'marginTop': '20px'})
])


# 콜백 함수 정의
@app.callback(
    Output('output-container', 'children'),
    [Input('region-dropdown', 'value'),
     Input('date-picker', 'date')]
)
def update_output(selected_region, selected_date):
    selected_date = pd.to_datetime(selected_date)
    filtered_data = data[(data['지역'] == selected_region) & (data['날짜'] == selected_date)]

    if not filtered_data.empty:
        row = filtered_data.iloc[0]
        return (
            f"호출 건수: {row['호출 건수']}건\n"
            f"이용 인원: {row['이용 인원']}명\n"
            f"운행 대수: {row['운행 대수']}대"
        )
    else:
        return "선택한 조건에 맞는 데이터가 없습니다."


# 앱 실행
if __name__ == '__main__':
    app.run_server(debug=True)