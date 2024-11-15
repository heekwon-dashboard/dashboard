# 필요한 라이브러리 임포트
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

# 대시보드 앱 초기화
app = dash.Dash(__name__)

# 레이아웃 정의
app.layout = html.Div([
    html.H1("Slider를 활용한 Dash 예제", style={'textAlign': 'center'}),

    # Slider 컴포넌트
    dcc.Slider(
        id='my-slider',
        min=0,
        max=100,
        step=1,
        value=50,
        marks={i: str(i) for i in range(0, 101, 10)},
        tooltip={"placement": "bottom", "always_visible": True}
    ),

    # Slider 값을 표시할 Div
    html.Div(id='slider-output', style={'marginTop': '20px', 'fontSize': '20px'})
])


# 콜백 함수 정의
@app.callback(
    Output('slider-output', 'children'),
    Input('my-slider', 'value')
)
def update_output(value):
    return f"선택한 값: {value}"


# 앱 실행
if __name__ == '__main__':
    app.run_server(debug=True)