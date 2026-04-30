VRP(Vehicle Routing Problem)

진행 단계 file(src): beginners.ipynb(단계별 수정 작업 내용들이 모두 담겨져 있습니다.)
최종 file: final.py(beginners.ipynb의 최종 작업을 final.py로 저장하였습니다)

추출된 결과물: src/dataset
-> 각 HUB에 대해 그리고 penalty 별 결과물이 담겨져 있습니다.

사용법
- CONFIG의 수치만 조종시키고 실행시키면 큰 이상은 없을 것이다.
- 원하는 penalty 값, vehicles, 출발지, 도착지를 설정하면 된다

주의사항
- 출발지 혹은 도착지를 선택할 때에는 반드시, csv의 data와 똑같이 입력해야 한다.
- 만일, 다른 data를 활용하길 원한다면 해당 자료는 반드시 4326 좌표형태로 되어있는 것을 활용해라
- 또한, 새로운 좌표가 더 생긴다면 그에 맞춰서 node를 생성해야 하고 outgoing.csv의 H3 cell에 대응하는 data값들을 찾아야 한다.
- 애니메이션은 kernel broken의 문제로 인해 특정 시간대의 gif만 출력되도록 하였다. 따라서, 시간 단위는 1시간 "0x:00 ~ 0x:59"의 형태임을 잊지 말아라.

참고사항
-outgoing.csv의 경우는 github에 업로드 하지 않았음. 따라서, 개인적으로 다운을 받아야함.
-저장 경로: src/ dataset

주의사항

## Requirements

- Python >= 3.13
- numpy >= 1.24
- pandas >= 2.0
- matplotlib >= 3.7
- ortools >= 9.8
