import subprocess
from datetime import datetime

def git_commit_push():
    """현재 변경사항을 자동으로 커밋하고 푸시합니다."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cmds = [
        ["git", "add", "."],
        ["git", "commit", "-m", f"Updated: {timestamp}"],
        ["git", "push", "origin", "main"]
    ]

    for cmd in cmds:
        print(f"$ {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ 명령어 실행 실패: {' '.join(cmd)}")
            print(f"오류: {e}")
            return False

    print("✅ 레포지토리 업데이트 완료!")
    return True

if __name__ == "__main__":
    git_commit_push()