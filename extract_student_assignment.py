import json
import csv
import re
from collections import defaultdict

def extract_file_info_from_attachment(attachment_string):
    """
    submitAttachments 문자열에서 파일 정보를 추출하는 함수
    형태: "파일타입 | 파일명 | URL"
    """
    if not attachment_string or attachment_string in ["첨부없음", "-"]:
        return None, None, None
    
    parts = attachment_string.split(" | ")
    if len(parts) >= 3:
        file_type = parts[0].strip()
        file_name = parts[1].strip()
        file_url = parts[2].strip()
        return file_type, file_name, file_url
    else:
        return None, attachment_string, None

def extract_student_assignments_from_json(json_file_path):
    """
    JSON 파일에서 학생별 과제 제출 정보를 추출하는 함수
    statsByMember에서 displayName과 assignments를 매칭
    """
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    print(f"📁 파일 읽기 완료. 데이터 타입: {type(data)}")
    
    # 학생별 제출 정보를 저장할 딕셔너리
    student_assignments = defaultdict(list)
    
    # statsByMember에서 학생 정보 처리
    if 'statsByMember' in data and isinstance(data['statsByMember'], list):
        print(f"👥 총 {len(data['statsByMember'])}명의 학생을 발견했습니다.")
        
        for member_data in data['statsByMember']:
            if 'member' not in member_data:
                continue
                
            # 학생 이름 추출
            member_info = member_data['member']
            student_name = member_info.get('displayName', '이름 없음')
            
            print(f"\n👤 학생: {student_name}")
            
            # assignments 찾기
            assignments = member_data.get('assignments', [])
            
            if not assignments:
                print(f"   ⚠️ assignments가 없습니다.")
                continue
                
            print(f"   📝 {len(assignments)}개의 과제를 확인 중...")
            
            for i, assignment in enumerate(assignments):
                if 'submitAttachments' in assignment and assignment['submitAttachments'] not in ["첨부없음", "-"]:
                    print(f"   📎 과제 {i+1}: 첨부파일 발견")
                    
                    # 파일 정보 추출
                    file_type, file_name, file_url = extract_file_info_from_attachment(assignment['submitAttachments'])
                    
                    # 과제 정보 저장
                    assignment_info = {
                        'subject': assignment.get('subject', '과제명 없음'),
                        'submit_subject': assignment.get('submitSubject', '제출 제목 없음'),
                        'file_type': file_type,
                        'file_name': file_name,
                        'file_url': file_url,
                        'submit_created': assignment.get('submitCreated', '날짜 없음'),
                        'submit_review': assignment.get('submitReview', '후기 없음')
                    }
                    
                    student_assignments[student_name].append(assignment_info)
                    print(f"      ✅ 추가됨: {file_name}")
                else:
                    print(f"   📝 과제 {i+1}: 첨부파일 없음")
    else:
        print("❌ 'statsByMember'를 찾을 수 없습니다.")
        print(f"사용 가능한 키들: {list(data.keys()) if isinstance(data, dict) else '딕셔너리가 아닙니다'}")
    
    print(f"\n🎯 최종 결과: {len(student_assignments)}명의 학생에서 첨부파일 발견")
    return student_assignments

def create_csv_file(student_assignments, output_file='student_assignments.csv'):
    """
    학생별 과제 정보를 CSV 파일로 저장하는 함수
    """
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            '학생이름', '과제명', '제출제목', '파일형식', 
            '파일명', '제출일시', '제출후기', '파일URL'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # 헤더 작성
        writer.writeheader()
        
        # 학생별로 정렬하여 작성
        for student_name in sorted(student_assignments.keys()):
            assignments = student_assignments[student_name]
            
            for assignment in assignments:
                writer.writerow({
                    '학생이름': student_name,
                    '과제명': assignment['subject'],
                    '제출제목': assignment['submit_subject'],
                    '파일형식': assignment['file_type'],
                    '파일명': assignment['file_name'],
                    '제출일시': assignment['submit_created'],
                    '제출후기': assignment['submit_review'],
                    '파일URL': assignment['file_url']
                })

def print_student_summary(student_assignments):
    """
    학생별 제출 현황 요약 출력
    """
    print("\n" + "="*60)
    print("📊 학생별 과제 제출 현황 요약")
    print("="*60)
    
    if not student_assignments:
        print("❌ 제출된 첨부파일이 없습니다.")
        return
    
    total_students = len(student_assignments)
    total_submissions = sum(len(assignments) for assignments in student_assignments.values())
    
    print(f"👥 총 학생 수: {total_students}명")
    print(f"📝 총 제출 건수: {total_submissions}건")
    print(f"📈 평균 제출 건수: {total_submissions/total_students:.1f}건/학생" if total_students > 0 else "")
    
    print("\n📋 학생별 상세 현황:")
    for student_name in sorted(student_assignments.keys()):
        assignments = student_assignments[student_name]
        print(f"  • {student_name}: {len(assignments)}건")

def main():
    json_file_path = "./rawdata/1st_class.json"
    csv_output_file = "student_assignments.csv"
    
    try:
        print("🔍 JSON 파일에서 학생별 과제 정보 추출 중...")
        student_assignments = extract_student_assignments_from_json(json_file_path)
        
        if not student_assignments:
            print("❌ 추출된 과제 정보가 없습니다.")
            return
        
        print(f"✅ {len(student_assignments)}명의 학생 정보를 추출했습니다.")
        
        # 요약 출력
        print_student_summary(student_assignments)
        
        # CSV 파일 생성
        print(f"\n💾 CSV 파일 생성 중: {csv_output_file}")
        create_csv_file(student_assignments, csv_output_file)
        
        print(f"✅ CSV 파일이 성공적으로 생성되었습니다: {csv_output_file}")
        
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {json_file_path}")
    except json.JSONDecodeError:
        print("❌ JSON 파일 형식이 올바르지 않습니다.")
    except Exception as e:
        print(f"❌ 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()
