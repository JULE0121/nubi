from math import asin, cos, radians, sin, sqrt


def calculate_distance(lat1, lon1, lat2, lon2):
    """위도·경도로 두 지점 사이의 구면 거리를 km 단위로 계산한다."""
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    )
    # 소수점 계산 오차로 값이 범위를 벗어나는 것을 방지한다.
    a = min(1.0, max(0.0, a))

    return 2 * 6371.0 * asin(sqrt(a))


if __name__ == "__main__":
    distance = calculate_distance(
        38.244892, 128.572088,
        38.264923, 128.557322,
    )
    print(f"관광지 간 거리: {distance:.2f} km")
