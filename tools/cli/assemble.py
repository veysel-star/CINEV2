import json
import subprocess
from pathlib import Path

def load_durum(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def resolve_shot_video(durum: dict, shot_id: str) -> Path:
    shots = durum.get("shots", {})
    shot = shots.get(shot_id)
    if not shot:
        raise RuntimeError(f"shot bulunamadı: {shot_id}")
    
    outputs = shot.get("outputs", {})
    preview_rel = outputs.get("preview.mp4")
    if not preview_rel:
        raise RuntimeError(f"{shot_id} için outputs['preview.mp4'] yok")
    
    video = Path(preview_rel)
    if not video.exists():
        raise RuntimeError(f"video bulunamadı: {video}")
    
    return video

def get_shot_list(durum: dict, args):
    if getattr(args, "film", None):
        films = durum.get("films", {})
        film = films.get(args.film)
        if not film:
            raise RuntimeError(f"film bulunamadı: {args.film}")
        
        timeline = film.get("timeline")
        if not timeline or not isinstance(timeline, list):
            raise RuntimeError(f"{args.film} için timeline yok veya geçersiz")
        
        return timeline
    
    if getattr(args, "shots", None):
        return [s.strip() for s in args.shots.split(",") if s.strip()]
    
    raise RuntimeError("--film veya --shots verilmelidir")

def build_list_file(videos, list_path: Path):
    with open(list_path, "w", encoding="utf-8") as f:
        for v in videos:
            f.write(f"file '{v.as_posix()}'\n")

def run_ffmpeg(list_path: Path, out_path: Path):
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_path),
        "-c", "copy",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)

def main(args):
    durum = load_durum(args.durum_json)
    shots = get_shot_list(durum, args)

    videos = []
    for shot_id in shots:
        videos.append(resolve_shot_video(durum, shot_id))

    tmp_list =Path("tmp_assemble_list.txt")
    build_list_file(videos, tmp_list)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    run_ffmpeg(tmp_list, out_path)
    print(f"[OK] film created: {out_path}")

if __name__ == "__main__":
    raise SystemExit("Use: python -m tools.cli assemble ...")

    
    





     