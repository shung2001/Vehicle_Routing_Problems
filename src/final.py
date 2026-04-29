import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import random
import csv

from matplotlib.patches import Circle
from matplotlib.animation import FuncAnimation

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp



CONFIG = {
    "num_vehicles": 1,
    "start_depot": "Depot_Beom_Gye",
    "end_depot": "Depot_Beom_Gye",
    "penalty": 6000,
    "output_folder": "범계",
    "output_prefix": "Depot_Beom_Gye",
    "designated_time": "08:00 ~ 08:59",
    "make_animation": True,

}

# ==================================================
# 1. 기본 데이터 모델 생성
# ==================================================
def create_data_model():
    BASE_DIR = Path.cwd()

    vertiport = pd.read_csv(
        BASE_DIR / "dataset" / "버티포트_일반_후보지.csv",
        encoding="cp949"
    )

    vertiport_hub = pd.read_csv(
        BASE_DIR / "dataset" / "핵심허브_경도_위도_명칭.csv",
        encoding="cp949"
    )

    distance_vertiport = pd.concat(
    [vertiport, vertiport_hub],
    ignore_index=True
    )

    distance_vertiport["id"] = range(len(distance_vertiport))

    # 핵심 허브, 허브 역시 depot 뿐만 아니라 일반 node로 사용하기 위해 중복 value를 추가. But, 구분하기 위해 앞에 Depot을 추가
    distance_vertiport.loc[14, "NAME"] = "Depot_Bundang_Townhall"
    distance_vertiport.loc[15, "NAME"] = "Depot_Gimpo_Airport"
    distance_vertiport.loc[16, "NAME"] = "Depot_Beom_Gye"
    distance_vertiport.loc[17, "NAME"] = "Depot_Kintex"
    distance_vertiport.loc[18, "NAME"] = "Depot_Gwang_Myeong"
    distance_vertiport.loc[19, "NAME"] = "Depot_Incheon_Airport"

    lats = distance_vertiport["y_latitude"].values
    lons = distance_vertiport["x_longtitude"].values

    node_to_name = dict(zip(distance_vertiport["id"], distance_vertiport["NAME"]))
    name_to_node = dict(zip(distance_vertiport["NAME"], distance_vertiport["id"]))

    n = len(distance_vertiport)
    distance_matrix = np.zeros((n, n), dtype=np.int64)

    for i in range(n):
        for j in range(n):
            distance_matrix[i, j] = haversine_distance(
                lats[i], lons[i],
                lats[j], lons[j]
            )

    data = {}
    data["distance_matrix"] = distance_matrix.tolist()
    data["num_vehicles"] = CONFIG["num_vehicles"]
    data["node_to_name"] = node_to_name
    data["name_to_node"] = name_to_node # CONFIG에서 입력한 명령어를 수행하기 위함

    data["starts"] = [name_to_node[CONFIG["start_depot"]]]
    data["ends"] = [name_to_node[CONFIG["end_depot"]]]

    return data


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    )

    c = 2 * np.arcsin(np.sqrt(a))
    return int(R * c)


# ==================================================
# 2. 수요 데이터 처리 / 시간대의 data를 가중치로 변환하는 초기작업
# ==================================================
def process_incheon(df): # df = incheon
    df = df.copy()

    df["Normal_Count"] = pd.to_numeric( # 간혹 csv에서 숫자이나, str로 인식하는 경우 존재. 따라서, to_numeric으로 int로 변형 + str이 이 함수에 적용 받으면, NaN.
        df["Normal_Count"],
        errors="coerce"
    )

    df = df.dropna(subset=["Normal_Count", "time"]) # NaN이 존재하는 행은 제거

    df["weight"] = df["Normal_Count"] / df["Normal_Count"].max() # 가중치 부여 방식: 최대값 나누기 각 value 값
    df["node_id"] = "Incheon_Airport" 

    return df[["time", "node_id", "weight"]]


def process_vertiport(df): # df = vertiport
    df = df.copy()

    df["outgoing_count"] = pd.to_numeric(
        df["outgoing_count"],
        errors="coerce"
    )

    df = df.dropna(subset=["outgoing_count", "time"])

    hour = pd.to_datetime(
        df["time"],
        format="%H:%M:%S",
        errors="coerce"
    ).dt.hour

    df["time"] = (
        hour.astype("Int64").astype(str).str.zfill(2) # 가지고 있는 data의 형태가 05:00의 형태이므로 앞에 이 형식에 맞는 코딩을 진행.
        + ":00 ~ "
        + hour.astype("Int64").astype(str).str.zfill(2)
        + ":59"
    )

    df["weight"] = df["outgoing_count"] / df["outgoing_count"].max()

    # cost_callback의 node_name과 맞추기 위해 NAME 사용
    df["node_id"] = df["NAME"] 

    return df[["time", "node_id", "weight"]]


# 위의 process_incheon과 process_vertiport의 계산과정을 통합하기 위함.
def merge_demand(df1, df2):
    return pd.concat([df1, df2], ignore_index=True)

# process_incheon과 process_vertiport에서 시간대 별로 계산한 값들을 표로 표현.
def build_time_dict(df):
    result = {}

    for t in df["time"].unique():
        sub = df[df["time"] == t]
        result[t] = dict(zip(sub["node_id"], sub["weight"]))

    return result


# 위의 과정을 최종적으로 정리한 부분
def demand():
    BASE_DIR = Path.cwd()

    incheon = pd.read_csv( 
        BASE_DIR / "dataset" / "인천공항_시간별_이용객수(2026.03).csv",
        encoding="utf-8-sig"
    )

    vertiport = pd.read_csv(
        BASE_DIR / "dataset" / "버티포트_지역의_시간대_별_인구유출_data.csv",
        encoding="utf-8-sig"
    )

    # SKT 데이터에서 공항 cell 제거, SKT 데이터의 인천공항 data는 매우 부정확하고 분석에 부정적인 영향을 미칠 것 같아. 제외함.
    vertiport = vertiport[
        vertiport["outgoing_cell"] != "8830e08c35fffff"
    ]

    incheon_df = process_incheon(incheon)
    vertiport_df = process_vertiport(vertiport)

    merged_demand = merge_demand(incheon_df, vertiport_df)
    time_demand = build_time_dict(merged_demand)

    print("시간대 개수:", len(time_demand))
    print("시간대 목록:", list(time_demand.keys()))

    return time_demand


# ==================================================
# 3. 비용 함수 
# ==================================================
def make_cost_callback(data, manager, time_demand, current_time):
    def cost_callback(from_index, to_index):
        # id를 node로 변환하는 작업
        from_node = int(manager.IndexToNode(from_index)) 
        to_node = int(manager.IndexToNode(to_index))

        distance = data["distance_matrix"][from_node][to_node] # id & haversine_matrix를 통해서 구한 distance_matrix에 node를 대입해 거리출력

        node_name = data["node_to_name"][to_node] # 도착지점 node를 출력(최종도착지점 X) + 도착지점의 이름과 node를 출력
        demand_weight = time_demand[current_time].get(node_name, 0) # 해당 시간대의 가중치 

        try:
            demand_weight = float(demand_weight)
        except:
            demand_weight = 0

        """해당 node는 각각 김포공항과 인천공항이다. 공항은 도심지와 비교적 거리가 떨어져 있다. 
        따라서, distance_cost를 측정할 때, 다른 depot node 대비 높은 cost가 출력될 것이다.
        하지만, 거리가 멀더라도 공항 특성상 수요가 분명 높은 지점이므로 의도적으로 cost를 낮추었다."""
        alpha = 2.0

        if to_node == 19: # 인천공항
            cost = distance * 0.1 / (1 + alpha * demand_weight) # distance에 0.1을 곱하고 분모에 alpha를 추가했다. 하지만, 아직 정확한 수치를 대입하지 못하였으므로 조금 더 분석을 진행해서 alpha와 상수의 적정값을 찾을 예정

        elif to_node == 15: # 김포공항, 비교적 공항에 더 가까워서
            cost = distance * 0.3 / (1 + alpha * demand_weight)

        else:
            cost = distance / (1 + alpha * demand_weight)

        return int(cost)

    return cost_callback


# ==================================================
# 4. 결과 출력
# ==================================================
def solution_to_text(data, manager, routing, solution, current_time):
    lines = []

    lines.append(f"\n===== {current_time} 결과 =====")
    lines.append(f"Objective: {solution.ObjectiveValue()}") # 궁극적으로 전페 cost를 측정하는 수치이고 objectiveValue()를 통해 최적화를 진행.

    max_route_distance = 0

    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        plan_output = f"Route for vehicle {vehicle_id}:\n"
        route_distance = 0

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            name = data["node_to_name"][node]

            plan_output += f" {name} -> "

            previous_index = index
            index = solution.Value(routing.NextVar(index))

            route_distance += routing.GetArcCostForVehicle(
                previous_index,
                index,
                vehicle_id
            )

        end_node = manager.IndexToNode(index)
        end_name = data["node_to_name"][end_node]

        plan_output += f"{end_name}\n"
        plan_output += f"Distance of the route: {route_distance}m\n"

        lines.append(plan_output)
        max_route_distance = max(max_route_distance, route_distance)

    lines.append(f"Maximum of the route distances: {max_route_distance}m")

    return "\n".join(lines)


def print_solution(data, manager, routing, solution, current_time):
    text = solution_to_text(data, manager, routing, solution, current_time)
    print(text)
    return text

# csv화 진행
def extract_route_records(data, manager, routing, solution, current_time):
    summary_records = []
    step_records = []

    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)

        route_nodes = []
        route_names = []
        total_real_distance = 0
        total_cost = 0
        step = 0

        while not routing.IsEnd(index):
            from_node = manager.IndexToNode(index)
            from_name = data["node_to_name"][from_node]

            route_nodes.append(from_node)
            route_names.append(from_name)

            previous_index = index
            index = solution.Value(routing.NextVar(index))

            to_node = manager.IndexToNode(index)
            to_name = data["node_to_name"][to_node]

            real_distance = data["distance_matrix"][from_node][to_node]
            arc_cost = routing.GetArcCostForVehicle(
                previous_index,
                index,
                vehicle_id
            )

            total_real_distance += real_distance
            total_cost += arc_cost
            route_efficiency = total_cost / total_real_distance if total_real_distance != 0 else 0
        
            step_records.append({
                "time": current_time,
                "vehicle_id": vehicle_id,
                "step": step,
                "from_node": from_node,
                "from_name": from_name,
                "to_node": to_node,
                "to_name": to_name,
                "real_distance": real_distance,
                "cost": arc_cost,
                "efficiency": route_efficiency,
                "real_distance": real_distance,
                "total_real_distance": total_real_distance,
                "objectives" : solution.ObjectiveValue()
            })

            step += 1

        end_node = manager.IndexToNode(index)
        end_name = data["node_to_name"][end_node]

        route_nodes.append(end_node)
        route_names.append(end_name)

        distance_list = []
        distance_list.append(total_real_distance)

        summary_records.append({
            "time": current_time,
            "vehicle_id": vehicle_id,
            "start_node": route_nodes[0],
            "end_node": route_nodes[-1],
            "route_nodes": " -> ".join(map(str, route_nodes)),
            "route_names": " -> ".join(route_names),
            "real_distance": total_real_distance,
            "cost": total_cost,
            "objectives" : solution.ObjectiveValue(),
            "total_real_distance": total_real_distance
        })

    return summary_records, step_records

# ==================================================
# 5. 경로 추출 및 애니메이션
# ==================================================
def extract_routes(data, manager, routing, solution):
    routes = []

    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        route = [manager.IndexToNode(index)]

        while not routing.IsEnd(index):
            index = solution.Value(routing.NextVar(index))
            route.append(manager.IndexToNode(index))

        routes.append(route)

    return routes


def animate_routes(data, manager, routing, solution, current_time):
    routes = extract_routes(data, manager, routing, solution)
    print("routes =", routes)

    pos = {
    0: (0, 0),

    # 상단 클러스터
    1: (-2, 5), 2: (2, 5), 3: (-4, 4), 4: (-3, 4),
    5: (1, 3), 6: (3, 3), 7: (-1, 2), 8: (2, 2),

    # 중간
    9: (1, 0), 10: (4, 0),

    # 하단 클러스터
    11: (-3, -2), 12: (-2, -2), 13: (-1, -3),
    14: (2, -3), 15: (-4, -4), 16: (3, -4),

    # 기존 허브
    17: (0, 4),
    18: (5, 1),
    19: (-5, -1),

}
    

    colors = [
        "tomato",
        "cornflowerblue",
        "mediumseagreen",
        "gold",
        "orchid",
        "turquoise"
    ]

    segments = []

    for vehicle_id, route in enumerate(routes):
        if len(route) <= 2 and route[0] == route[-1]:
            continue

        for i in range(len(route) - 1):
            a = route[i]
            b = route[i + 1]
            segments.append((vehicle_id, a, b))

    print("segments =", segments)

    if len(segments) == 0:
        print("애니메이션 생성할 경로가 없습니다.")
        return None

    fig, ax = plt.subplots(figsize=(10, 7))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("black")

    ax.set_xlim(-7, 7)
    ax.set_ylim(-7, 7)
    ax.set_xticks(range(-7, 7))
    ax.set_yticks(range(-7, 7))
    ax.grid(True, color="gray", alpha=0.5, linewidth=0.8)
    ax.set_aspect("equal")
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

    for node, (x, y) in pos.items():
        if node in data["starts"]:
            face = "lightgray"
            edge = "black"
            txt = "black"
        else:
            face = "white"
            edge = "white"
            txt = "black"

        circle = Circle(
            (x, y),
            0.23,
            facecolor=face,
            edgecolor=edge,
            linewidth=2,
            zorder=5
        )

        ax.add_patch(circle)
        ax.text(
            x,
            y,
            str(node),
            ha="center",
            va="center",
            fontsize=12,
            color=txt,
            zorder=6
        )

    drawn_artists = []

    def update(frame):
        
        vehicle_id, a, b = segments[frame]
        color = colors[vehicle_id % len(colors)]

        x1, y1 = pos[a]
        x2, y2 = pos[b]

        line, = ax.plot(
            [x1, x2],
            [y1, y2],
            color=color,
            linewidth=4,
            solid_capstyle="round",
            zorder=2
        )

        arrow = ax.annotate(
            "",
            xy=(x1 * 0.45 + x2 * 0.55, y1 * 0.45 + y2 * 0.55),
            xytext=(x1 * 0.55 + x2 * 0.45, y1 * 0.55 + y2 * 0.45),
            arrowprops=dict(
                arrowstyle="-|>",
                color=color,
                lw=2.2,
                mutation_scale=22
            ),
            zorder=3
        )

        drawn_artists.append(line)
        drawn_artists.append(arrow)

        ax.set_title(
            f"{current_time} | Step {frame + 1}: vehicle {vehicle_id}, {a} -> {b}",
            color="white"
        )

        return drawn_artists

    anim = FuncAnimation(
        fig,
        update,
        frames=len(segments),
        interval=800,
        repeat=False,
        blit=False
    )

    plt.tight_layout()

    safe_time = (
        current_time
        .replace(":", "")
        .replace(" ", "")
        .replace("~", "_")
    )
    
    BASE_DIR = Path.cwd()

    save_path = BASE_DIR /"dataset"/"vrp_animation_{safe_time}.gif"

    anim.save(save_path, writer="pillow", fps=1)
    print(f"GIF 저장 완료: {save_path}")

    plt.show()

    return anim


# ==================================================
# 6. 시간대별 VRP 실행
# ==================================================
def run_vrp_for_time(current_time, time_demand, make_animation=False, penalty = 2000):
    data = create_data_model()

    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]),
        data["num_vehicles"],
        data["starts"],
        data["ends"]
    ) # node의 이동 참고자료

    routing = pywrapcp.RoutingModel(manager) # manager를 기반으로 routing을 진행

    cost_callback = make_cost_callback(
        data,
        manager,
        time_demand,
        current_time
    )

    transit_callback_index = routing.RegisterTransitCallback(cost_callback)

    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data["distance_matrix"][from_node][to_node]

    distance_callback_index = routing.RegisterTransitCallback(distance_callback)

    # 일부 노드는 방문하지 않아도 되게 허용


    optional_nodes = []

    customer_nodes = list(range(len(data["distance_matrix"])))  # 일반 수요 노드만

    for node in customer_nodes:
        routing.AddDisjunction(
            [manager.NodeToIndex(node)],
            penalty
        )
        optional_nodes.append(node)

    print("penalty =", penalty)
    print("optional node count =", len(optional_nodes))
    print("optional nodes =", optional_nodes)
    print("expected penalty if all skipped =", len(optional_nodes) * penalty)   

    dimension_name = "Distance"

    routing.AddDimension(
        distance_callback_index,
        0,
        1000000, # m 단위임 / km안으로 비행을 완료하라.
        True,
        dimension_name
    )

    distance_dimension = routing.GetDimensionOrDie(dimension_name) # Distance라는 이름의 dimension을 가져와라
    #distance_dimension.SetGlobalSpanCostCoefficient(100)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC # 가장 비용이 적은 간선을 골라 경로를 생성
    )
    search_parameters.time_limit.seconds = 40

    solution = routing.SolveWithParameters(search_parameters) # 지금까지 정의한 모든 조건을 가지고 최적 경로를 계산

    if solution:
        result_text = print_solution(
            data,
            manager,
            routing,
            solution,
            current_time
        )

        if make_animation:
            anim = animate_routes(
                data,
                manager,
                routing,
                solution,
                current_time
            )
            print(anim)

        return {
            "text": result_text,
            "data": data,
            "manager": manager,
            "routing": routing,
            "solution": solution
        }

    else:
        result_text = f"\n===== {current_time} 결과 없음 ====="
        print(result_text)

        return {
            "text": result_text,
            "data": None,
            "manager": None,
            "routing": None,
            "solution": None
        }


# ==================================================
# 7. 전체 실행
# ==================================================
def main():
    BASE_DIR = Path.cwd()
    time_demand = demand()

    all_summary_records = []
    all_step_records = []

    penalty = CONFIG["penalty"]

    for current_time in time_demand.keys():
        result = run_vrp_for_time(
            current_time,
            time_demand,
            make_animation=False,
            penalty=penalty
        )

        if result is None or result["solution"] is None:
            continue

        summary_records, step_records = extract_route_records(
            result["data"],
            result["manager"],
            result["routing"],
            result["solution"],
            current_time
        )

        all_summary_records.extend(summary_records)
        all_step_records.extend(step_records)

    summary_df = pd.DataFrame(all_summary_records)
    steps_df = pd.DataFrame(all_step_records)

    output_dir = BASE_DIR / "dataset" / CONFIG["output_folder"]
    output_dir.mkdir(parents=True, exist_ok=True)

    output_prefix = CONFIG["output_prefix"]

    summary_df.to_csv(
        output_dir / f"{output_prefix}_route_summary_{penalty}.csv",
        index=False,
        encoding="utf-8-sig"
    )

    steps_df.to_csv(
        output_dir / f"{output_prefix}_route_steps_{penalty}.csv",
        index=False,
        encoding="utf-8-sig"
    )

    run_vrp_for_time(
        CONFIG["designated_time"],
        time_demand,
        make_animation=CONFIG["make_animation"],
        penalty=penalty
    )

    print("CSV 저장 완료")
    print(f'{CONFIG["designated_time"]} 시간대의 애니메이션 저장 완료')




if __name__ == "__main__":
    main()