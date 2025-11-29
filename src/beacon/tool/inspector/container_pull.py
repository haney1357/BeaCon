import subprocess

def container_pull(image: str):
	try:
		p = subprocess.run(
			["docker", "image", "ls", "--format", '"{{.Repository}}"', image],
			stdout=subprocess.PIPE
		)
		if not p.stdout:
			print(f"\tPulling {image}...")
			subprocess.run(["docker", "pull", image])
	except subprocess.CalledProcessError as e:
		print(f"Script Failed {image} - ({e.returncode}): {e.stderr}")
