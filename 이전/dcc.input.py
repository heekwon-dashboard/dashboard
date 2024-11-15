# 필요한 라이브러리 임포트
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

# 대시보드 앱 초기화
app = dash.Dash(__name__)

# 레이아웃 정의
app.layout = html.Div([
    html.H1("Input 컴포넌트를 활용한 Dash 예제", style={'textAlign': 'center'}),

    # Input 컴포넌트
    dcc.Input(
        id='text-input',
        type='text',
        placeholder='텍스트를 입력하세요',
        style={'marginBottom': '10px', 'fontSize': '16px'}
    ),

    # Input 값을 표시할 Div
    html.Div(id='input-output', style={'fontSize': '20px'})
])

# 콜백 함수 정의
@app.callback(
    Output('input-output', 'children'),
    Input('text-input', 'value')
)
def update_output(value):
    if value:
        return f"입력한 텍스트: {value}"
    else:
        return "텍스트를 입력하세요."

# 앱 실행
if __name__ == '__main__':
    app.run_server(debug=True)