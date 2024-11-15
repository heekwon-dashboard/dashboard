# 필요한 라이브러리 임포트
import dash
from dash import dcc, html

# 대시보드 앱 초기화
app = dash.Dash(__name__)

# 레이아웃 정의
app.layout = html.Div([
    html.H1("Tabs 컴포넌트를 활용한 Dash 예제", style={'textAlign': 'center'}),

    # Tabs 컴포넌트
    dcc.Tabs([
        dcc.Tab(label='탭 1', children=[
            html.Div([
                html.H3("첫 번째 탭의 콘텐츠"),
                html.P("이곳은 탭 1의 내용을 표시하는 곳입니다.")
            ])
        ]),
        dcc.Tab(label='탭 2', children=[
            html.Div([
                html.H3("두 번째 탭의 콘텐츠"),
                html.P("이곳은 탭 2의 내용을 표시하는 곳입니다.")
            ])
        ])
    ])
])

# 앱 실행
if __name__ == '__main__':
    app.run_server(debug=True)