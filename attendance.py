import cv2
import face_recognition
import pickle
import mysql.connector
from datetime import datetime, timedelta

# Connect to MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="attendance_db"
)
cursor = conn.cursor()

# ---------------- Register Student ----------------
def register_student(name, roll_no):
    cap = cv2.VideoCapture(0)
    print("Capturing face for registration... Press 'q' to capture.")

    while True:
        ret, frame = cap.read()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)

        # Draw green box around detected faces
        for (top, right, bottom, left) in face_locations:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

        cv2.imshow("Register Student", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            if face_locations:
                encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                if encodings:
                    encoding_data = pickle.dumps(encodings[0])
                    cursor.execute("INSERT INTO students (name, roll_no, face_encoding) VALUES (%s, %s, %s)",
                                   (name, roll_no, encoding_data))
                    conn.commit()
                    print("Student registered successfully!")
            break

    cap.release()
    cv2.destroyAllWindows()

# ---------------- Take Attendance ----------------
def take_attendance():
    cap = cv2.VideoCapture(0)

    # Load students from DB
    cursor.execute("SELECT id, name, roll_no, face_encoding FROM students")
    students = cursor.fetchall()

    known_encodings = []
    student_ids = []
    student_names = {}
    for s in students:
        student_ids.append(s[0])
        known_encodings.append(pickle.loads(s[3]))
        student_names[s[0]] = s[1]

    seen_start = {}  # track when a student was first seen

    print("Starting attendance... Press 'q' to stop.")

    while True:
        ret, frame = cap.read()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces(known_encodings, face_encoding)
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)

            best_match_index = None
            if matches:
                best_match_index = min(range(len(face_distances)), key=lambda i: face_distances[i])

            if best_match_index is not None and matches[best_match_index]:
                matched_id = student_ids[best_match_index]
                name = student_names[matched_id]

                # Draw blue box and name
                cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 0), 2)
                cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

                now = datetime.now()

                if matched_id not in seen_start:
                    seen_start[matched_id] = now
                else:
                    # Check if seen continuously for 2 minutes
                    if now - seen_start[matched_id] >= timedelta(minutes=0.1):
                        cursor.execute("INSERT INTO attendance (student_id, date, time, status) VALUES (%s, %s, %s, %s)",
                                       (matched_id, now.date(), now.time(), "Present"))
                        conn.commit()
                        print(f"{name} marked Present!")
                        # Reset so they aren’t marked multiple times
                        seen_start[matched_id] = now + timedelta(hours=1)

        cv2.imshow("Attendance System", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# ---------------- Main Menu ----------------
print("Choose an option:")
print("1. Register Student")
print("2. Take Attendance")

choice = input("Enter choice (1/2): ")

if choice == "1":
    name = input("Enter student name: ")
    roll_no = input("Enter roll number: ")
    register_student(name, roll_no)
elif choice == "2":
    take_attendance()
else:
    print("Invalid choice!")
