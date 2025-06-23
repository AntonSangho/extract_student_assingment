import json
import os
import requests
import urllib.parse
from urllib.parse import urlparse
import time
import glob
from collections import defaultdict

def sanitize_filename(filename):
    """
    파일명에서 사용할 수 없는 문자를 제거하거나 대체하는 함수
    """
    # Windows에서 사용할 수 없는 문자들
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # 파일명 길이 제한 (255자)
    if len(filename) > 200:  # 확장자 여유분 고려
        filename = filename[:200]
    
    return filename.strip()

def get_file_extension_from_url(url):
    """
    URL에서 파일 확장자를 추출하는 함수
    """
    parsed_url = urlparse(url)
    path = parsed_url.path
    
    # URL에서 확장자 추출
    if '.' in path:
        return os.path.splitext(path)[1]
    
    return ''

def get_file_extension_from_type(file_type):
    """
    파일 타입에서 확장자를 추출하는 함수
    """
    type_mapping = {
        'application/pdf': '.pdf',
        'application/haansofthwp': '.hwp',
        'application/haansofthwpx': '.hwpx',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'text/plain': '.txt',
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif'
    }
    
    return type_mapping.get(file_type, '')

def download_file(url, file_path, max_retries=3):
    """
    URL에서 파일을 다운로드하는 함수
    """
    for attempt in range(max_retries):
        try:
            print(f"    📥 다운로드 시도 {attempt + 1}/{max_retries}: {os.path.basename(file_path)}")
            
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # 파일 크기 확인
            content_length = response.headers.get('content-length')
            if content_length:
                file_size = int(content_length)
                print(f"        📊 파일 크기: {file_size:,} bytes")
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"        ✅ 다운로드 완료")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"        ❌ 다운로드 실패 (시도 {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"        ⏳ {2 ** attempt}초 후 재시도...")
                time.sleep(2 ** attempt)
            
        except Exception as e:
            print(f"        ❌ 예상치 못한 오류: {e}")
            break
    
    return False

def extract_file_info_from_attachment(attachment_string):
    """
    submitAttachments 문자열에서 파일 정보를 추출하는 함수
    """
    if not attachment_string or attachment_string in ["첨부없음", "-"]:
        return None, None, None
    
    parts = attachment_string.split(" | ")
    if len(parts) >= 3:
        file_type = parts[0].strip()
        file_name = parts[1].strip()
        file_url = parts[2].strip()
        
        # URL에서 불필요한 파일 타입 정보 제거
        url_lines = file_url.split('\n')
        clean_url = url_lines[0].strip()
        
        return file_type, file_name, clean_url
    else:
        # 파일 타입 정보가 섞여있는 경우 처리
        lines = attachment_string.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('https://'):
                return None, attachment_string, line
        
        return None, attachment_string, None

def process_json_file(json_file_path, base_download_folder):
    """
    단일 JSON 파일을 처리하여 학생별 파일을 다운로드하는 함수
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except Exception as e:
        print(f"❌ JSON 파일 읽기 실패: {e}")
        return {}
    
    filename = os.path.basename(json_file_path)
    class_name = os.path.splitext(filename)[0]
    
    print(f"\n📂 {filename} 처리 중...")
    
    # 클래스별 폴더 생성
    class_folder = os.path.join(base_download_folder, class_name)
    if not os.path.exists(class_folder):
        os.makedirs(class_folder)
        print(f"   📁 클래스 폴더 생성: {class_folder}")
    
    download_stats = {
        'total_files': 0,
        'successful_downloads': 0,
        'failed_downloads': 0,
        'students_processed': 0
    }
    
    # statsByMember에서 학생 정보 처리
    if 'statsByMember' in data and isinstance(data['statsByMember'], list):
        print(f"   👥 총 {len(data['statsByMember'])}명의 학생 확인")
        
        for member_data in data['statsByMember']:
            if 'member' not in member_data:
                continue
            
            # 학생 이름 추출
            member_info = member_data['member']
            student_name = member_info.get('displayName', '이름_없음')
            
            # 학생별 폴더 생성
            student_folder = os.path.join(class_folder, sanitize_filename(student_name))
            if not os.path.exists(student_folder):
                os.makedirs(student_folder)
            
            print(f"   👤 {student_name} 처리 중...")
            
            # assignments 찾기
            assignments = member_data.get('assignments', [])
            
            if not assignments:
                print(f"      ⚠️ 과제가 없습니다.")
                continue
            
            student_files = 0
            student_downloads = 0
            
            for i, assignment in enumerate(assignments):
                if 'submitAttachments' in assignment and assignment['submitAttachments'] not in ["첨부없음", "-"]:
                    # 파일 정보 추출
                    file_type, file_name, file_url = extract_file_info_from_attachment(assignment['submitAttachments'])
                    
                    if not file_url or not file_url.startswith('https://'):
                        print(f"      ⚠️ 유효하지 않은 URL: {assignment['submitAttachments'][:50]}...")
                        continue
                    
                    student_files += 1
                    download_stats['total_files'] += 1
                    
                    # 파일명 정리
                    if file_name:
                        clean_filename = sanitize_filename(file_name)
                    else:
                        clean_filename = f"과제_{i+1}"
                    
                    # 확장자 추가
                    if not os.path.splitext(clean_filename)[1]:  # 확장자가 없다면
                        ext = get_file_extension_from_type(file_type) or get_file_extension_from_url(file_url)
                        if ext:
                            clean_filename += ext
                    
                    # 중복 파일명 처리
                    counter = 1
                    original_filename = clean_filename
                    file_path = os.path.join(student_folder, clean_filename)
                    
                    while os.path.exists(file_path):
                        name, ext = os.path.splitext(original_filename)
                        clean_filename = f"{name}_{counter}{ext}"
                        file_path = os.path.join(student_folder, clean_filename)
                        counter += 1
                    
                    # 파일 다운로드
                    if download_file(file_url, file_path):
                        student_downloads += 1
                        download_stats['successful_downloads'] += 1
                        
                        # 파일 정보를 텍스트 파일로 저장 (선택사항)
                        info_file = os.path.join(student_folder, f"{os.path.splitext(clean_filename)[0]}_정보.txt")
                        with open(info_file, 'w', encoding='utf-8') as f:
                            f.write(f"과제명: {assignment.get('subject', '없음')}\n")
                            f.write(f"제출제목: {assignment.get('submitSubject', '없음')}\n")
                            f.write(f"제출일시: {assignment.get('submitCreated', '없음')}\n")
                            f.write(f"제출후기: {assignment.get('submitReview', '없음')}\n")
                            f.write(f"파일타입: {file_type}\n")
                            f.write(f"원본URL: {file_url}\n")
                    else:
                        download_stats['failed_downloads'] += 1
                    
                    # 다운로드 간격 (서버 부하 방지)
                    time.sleep(0.5)
            
            if student_files > 0:
                download_stats['students_processed'] += 1
                print(f"      📊 {student_name}: {student_downloads}/{student_files} 파일 다운로드 성공")
            else:
                print(f"      ⚠️ {student_name}: 다운로드할 파일이 없습니다.")
    
    else:
        print("   ❌ 'statsByMember'를 찾을 수 없습니다.")
    
    return download_stats

def main():
    rawdata_folder = "rawdata"
    download_folder = "downloads"
    
    # downloads 폴더 생성
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
        print(f"📁 {download_folder} 폴더를 생성했습니다.")
    
    print("🔍 rawdata 폴더에서 JSON 파일들을 찾는 중...")
    
    # JSON 파일들 찾기
    json_pattern = os.path.join(rawdata_folder, "*.json")
    json_files = glob.glob(json_pattern)
    
    if not json_files:
        print(f"❌ {rawdata_folder} 폴더에서 JSON 파일을 찾을 수 없습니다.")
        return
    
    print(f"📁 총 {len(json_files)}개의 JSON 파일을 발견했습니다.")
    print("="*60)
    
    # 전체 통계
    total_stats = {
        'total_files': 0,
        'successful_downloads': 0,
        'failed_downloads': 0,
        'students_processed': 0
    }
    
    # 각 JSON 파일 처리
    for json_file in sorted(json_files):
        file_stats = process_json_file(json_file, download_folder)
        
        # 통계 누적
        for key in total_stats:
            total_stats[key] += file_stats.get(key, 0)
    
    # 전체 결과 요약
    print("\n" + "="*60)
    print("📊 전체 다운로드 결과 요약")
    print("="*60)
    print(f"📁 처리된 JSON 파일: {len(json_files)}개")
    print(f"👥 파일이 있는 학생: {total_stats['students_processed']}명")
    print(f"📥 총 다운로드 시도: {total_stats['total_files']}건")
    print(f"✅ 성공적인 다운로드: {total_stats['successful_downloads']}건")
    print(f"❌ 실패한 다운로드: {total_stats['failed_downloads']}건")
    
    if total_stats['total_files'] > 0:
        success_rate = (total_stats['successful_downloads'] / total_stats['total_files']) * 100
        print(f"📈 성공률: {success_rate:.1f}%")
    
    print(f"\n💾 다운로드된 파일들은 '{download_folder}' 폴더에 저장되었습니다.")

if __name__ == "__main__":
    main()
