from django.shortcuts import render
from django.http import JsonResponse
from .models import Student, Attendance
import cv2, face_recognition, pickle
from datetime import datetime, timedelta

def home(request):
    return render(request, "attendance/home.html")

def register_student(request):
    if request.method == "POST":
        name = request.POST["name"]
        roll_no = request.POST["roll_no"]

        cap = cv2.VideoCapture(0)
        encodings_list = []

        # Define the angles we want to capture
        angle_instructions = ["Look straight", "Turn left", "Turn right", "Look up", "Look down"]
        angle_index = 0
        total_angles = len(angle_instructions)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)  # ✅ Fix mirror issue
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)

            # Draw green box if face detected
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

            # Show current instruction + progress counter
            cv2.putText(frame, angle_instructions[angle_index],
                        (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            cv2.putText(frame, f"Captured {angle_index}/{total_angles}",
                        (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            cv2.imshow("Register Student", frame)

            key = cv2.waitKey(1)
            if key == ord('c') and face_locations:
                encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                if encodings:
                    encodings_list.append(encodings[0])
                    print(f"Captured: {angle_instructions[angle_index]}")
                    angle_index += 1
                    if angle_index >= total_angles:
                        print("✅ All angles captured")
                        break
            elif key == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

        if encodings_list:
            # Save all encodings (not just one)
            encoding_data = pickle.dumps(encodings_list)
            Student.objects.create(name=name, roll_no=roll_no, face_encoding=encoding_data)
            return JsonResponse({"message": f"Student {name} registered successfully with {len(encodings_list)} angles!"})
        return JsonResponse({"error": "No face detected"})



def take_attendance(request):
    cap = cv2.VideoCapture(0)
    #cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)   # Width
    #cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # Height
    students = Student.objects.all()

    # Load multiple encodings per student
    known_encodings = []
    student_ids = []
    student_names = {}
    for s in students:
        encodings_list = pickle.loads(s.face_encoding)
        for enc in encodings_list:
            known_encodings.append(enc)
            student_ids.append(s.id)
            student_names[s.id] = s.name

    seen_start = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations) 

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            # ✅ Use stricter tolerance to avoid false matches
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.5)
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)

            if True in matches:
                best_match_index = min(range(len(face_distances)), key=lambda i: face_distances[i])
                if matches[best_match_index]:
                    matched_id = student_ids[best_match_index]
                    name = student_names[matched_id]

                    cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 0), 2)
                    cv2.putText(frame, name, (left, top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

                    now = datetime.now()
                    if matched_id not in seen_start:
                        seen_start[matched_id] = now
                    else:
                        if now - seen_start[matched_id] >= timedelta(minutes=0.2):
                            Attendance.objects.create(
                                student_id=matched_id,
                                date=now.date(),
                                time=now.time(),
                                status="Present"
                            )
                            seen_start[matched_id] = now + timedelta(hours=1)
            else:
                # ✅ Unknown face → ignore, don’t assign wrong name
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.putText(frame, "Unknown", (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

        cv2.namedWindow("Attendance System", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Attendance System", 800, 600)
        cv2.imshow("Attendance System", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return JsonResponse({"message": "Attendance session ended"})


def view_database(request):
    students = Student.objects.all()
    attendance = Attendance.objects.select_related("student").all()
    return render(request, "attendance/database.html", {
        "students": students,
        "attendance": attendance
    })