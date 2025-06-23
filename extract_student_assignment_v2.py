import json
import csv
import re
import os
import glob
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
    
    # 학생별 제출 정보를 저장할 딕셔너리
    student_assignments = defaultdict(list)
    
    # statsByMember에서 학생 정보 처리
    if 'statsByMember' in data and isinstance(data['statsByMember'], list):
        for member_data in data['statsByMember']:
            if 'member' not in member_data:
                continue
                
            # 학생 이름 추출
            member_info = member_data['member']
            student_name = member_info.get('displayName', '이름 없음')
            
            # assignments 찾기
            assignments = member_data.get('assignments', [])
            
            if not assignments:
                continue
            
            for assignment in assignments:
                if 'submitAttachments' in assignment and assignment['submitAttachments'] not in ["첨부없음", "-"]:
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
    
    return student_assignments

def create_csv_file(student_assignments, output_file):
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

def print_file_summary(json_file, student_assignments):
    """
    파일별 처리 결과 요약 출력
    """
    filename = os.path.basename(json_file)
    total_students = len(student_assignments)
    total_submissions = sum(len(assignments) for assignments in student_assignments.values())
    
    print(f"📄 {filename}")
    print(f"   👥 학생 수: {total_students}명")
    print(f"   📝 제출 건수: {total_submissions}건")
    
    if total_students > 0:
        print(f"   📋 학생별 제출 현황:")
        for student_name in sorted(student_assignments.keys()):
            assignments = student_assignments[student_name]
            print(f"      • {student_name}: {len(assignments)}건")
    else:
        print(f"   ❌ 제출된 첨부파일 없음")

def process_single_json_file(json_file_path):
    """
    단일 JSON 파일을 처리하는 함수
    """
    try:
        # JSON에서 학생 과제 정보 추출
        student_assignments = extract_student_assignments_from_json(json_file_path)
        
        # 파일명에서 확장자 제거하고 CSV 파일명 생성
        base_filename = os.path.splitext(os.path.basename(json_file_path))[0]
        csv_output_file = f"./results/{base_filename}.csv"
        
        # 결과 요약 출력
        print_file_summary(json_file_path, student_assignments)
        
        # CSV 파일 생성
        if student_assignments:
            create_csv_file(student_assignments, csv_output_file)
            print(f"   ✅ CSV 생성: {csv_output_file}")
        else:
            print(f"   ⚠️ 생성할 데이터가 없어 CSV 파일을 생성하지 않았습니다.")
        
        return len(student_assignments), sum(len(assignments) for assignments in student_assignments.values())
        
    except Exception as e:
        print(f"   ❌ 오류 발생: {e}")
        return 0, 0

def find_json_files(folder_path):
    """
    폴더에서 JSON 파일들을 찾는 함수
    """
    if not os.path.exists(folder_path):
        print(f"❌ 폴더를 찾을 수 없습니다: {folder_path}")
        return []
    
    # .json 확장자를 가진 모든 파일 찾기
    json_pattern = os.path.join(folder_path, "*.json")
    json_files = glob.glob(json_pattern)
    
    return json_files

def main():
    rawdata_folder = "rawdata"
    
    print("🔍 rawdata 폴더에서 JSON 파일들을 찾는 중...")
    
    # JSON 파일들 찾기
    json_files = find_json_files(rawdata_folder)
    
    if not json_files:
        print(f"❌ {rawdata_folder} 폴더에서 JSON 파일을 찾을 수 없습니다.")
        print("폴더 구조를 확인해주세요.")
        return
    
    print(f"📁 총 {len(json_files)}개의 JSON 파일을 발견했습니다.")
    print("="*60)
    
    # 전체 통계
    total_processed_students = 0
    total_submissions = 0
    successfully_processed = 0
    
    # 각 JSON 파일 처리
    for json_file in sorted(json_files):
        print(f"\n🔄 처리 중: {os.path.basename(json_file)}")
        
        students_count, submissions_count = process_single_json_file(json_file)
        
        if students_count > 0:
            successfully_processed += 1
            total_processed_students += students_count
            total_submissions += submissions_count
    
    # 전체 결과 요약
    print("\n" + "="*60)
    print("📊 전체 처리 결과 요약")
    print("="*60)
    print(f"📁 처리된 JSON 파일: {len(json_files)}개")
    print(f"✅ 성공적으로 처리된 파일: {successfully_processed}개")
    print(f"👥 총 처리된 학생 수: {total_processed_students}명")
    print(f"📝 총 제출 건수: {total_submissions}건")
    
    if successfully_processed > 0:
        print(f"📈 평균 제출 건수: {total_submissions/total_processed_students:.1f}건/학생" if total_processed_students > 0 else "")
        print(f"💾 생성된 CSV 파일: {successfully_processed}개")

if __name__ == "__main__":
    main()
