import anki_vector
from anki_vector.util import degrees, Distance
import math


def create_ascii_graph(distances: dict[int, float]) -> None:
    """Create a simple and clear ASCII representation of the distances and angles from center point."""
    LINES = 40
    COLUMNS = 100
    center_x = COLUMNS // 2
    center_y = LINES // 2
    graph_matrix = [[" " for _ in range(COLUMNS)] for _ in range(LINES)]
    max_distance = max(distances.values())
    for angle, distance in distances.items():
        # Calculate the position in the matrix based on the angle and distance using trigonometry
        radians = angle * (3.14159 / 180)
        x = math.cos(radians) * (distance / max_distance) * (COLUMNS // 2)
        y = math.sin(radians) * (distance / max_distance) * (LINES // 2)
        # Convert to matrix coordinates
        matrix_x = int(center_x + x)
        matrix_y = int(center_y - y)  # Invert y-axis for correct display
        # Ensure the coordinates are within bounds
        if 0 <= matrix_x < COLUMNS and 0 <= matrix_y < LINES:
            graph_matrix[matrix_y][matrix_x] = "." if distance == 400.0 else "#"
    graph_matrix[center_y][center_x] = "O"  # Mark the center point
    # Print the graph
    for line in graph_matrix:
        print("".join(line))


def main():
    args = anki_vector.util.parse_command_args()

    # Connect to Vector
    with anki_vector.Robot(args.serial, enable_nav_map_feed=True) as robot:
        # Get the distance from Vector to the nearest object in front of it
        # robot.nav_map ## TODO: Explore
        step = 30
        steps = range(0, 360, step)
        print("Expected: ", steps)
        distances = {}
        for angle in steps:
            robot.behavior.turn_in_place(degrees(step))
            distance: Distance = robot.proximity.last_sensor_reading.distance
            distances[angle] = distance.distance_mm
            print("At ", angle, " degrees distance to nearest object is", distance.distance_mm, "mm")
        
        print("Distances collected: ", distances)

        create_ascii_graph(distances)


if __name__ == "__main__":
    main()