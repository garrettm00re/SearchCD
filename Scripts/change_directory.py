import os
## Currently irrelevant function

def generate_cd_command():
    path = input("Please enter the path to change to: ")
    corrected_path = path.replace("\\", "/")  # For Git Bash compatibility
    shell = os.getenv('SHELL')
    
    if shell and 'bash' in shell:
        # For Git Bash
        print(f'cd "{corrected_path}"')
    elif shell and 'powershell' in shell.lower():
        # For PowerShell
        print(f'Set-Location -Path "{path}"')
    else:
        # For cmd
        print(f'cd /d {path}')

if __name__ == "__main__":
    generate_cd_command()
