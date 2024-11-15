# 필요한 라이브러리 임포트
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

# 대시보드 앱 초기화
app = dash.Dash(__name__)

# 레이아웃 정의
app.layout = html.Div([
    html.H1("RadioItems 컴포넌트를 활용한 Dash 예제", style={'textAlign': 'center'}),

    # RadioItems 컴포넌트
    dcc.RadioItems(
        id='radio-options',
        options=[
            {'label': '옵션 1', 'value': 'option1'},
            {'label': '옵션 2', 'value': 'option2'},
            {'label': '옵션 3', 'value': 'option3'}
        ],
        value='option1',  # 초기 선택값
        style={'marginBottom': '20px'}
    ),

    # 선택된 옵션의 결과를 표시할 Div
    html.Div(id='radio-output', style={'fontSize': '20px'})
])

# 콜백 함수 정의
@app.callback(
    Output('radio-output', 'children'),
    Input('radio-options', 'value')
)
def update_output(selected_option):
    return f"선택한 옵션: {selected_option}"

# 앱 실행
if __name__ == '__main__':
    app.run_server(debug=True)