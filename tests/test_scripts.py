"""Tests for the copilot tool installation scripts (convert.sh and install.sh).

These tests validate that the shell scripts correctly convert agent files
from the standard agency-agents frontmatter format to GitHub Copilot agent
format, and install them into the appropriate project directory.
"""
import os
import subprocess
import tempfile
import unittest


SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts",
)


def _create_agent_file(directory: str, filename: str, name: str,
                       description: str, body: str) -> str:
    """Create a sample agent .md file with frontmatter.

    Parameters:
    directory (str): Directory to write the file in.
    filename (str): Name of the .md file.
    name (str): Agent name for the frontmatter.
    description (str): Agent description for the frontmatter.
    body (str): Markdown body below the frontmatter.

    Returns:
    str: Absolute path to the created file.
    """
    filepath = os.path.join(directory, filename)
    content = f"---\nname: {name}\ndescription: {description}\ncolor: green\n---\n\n{body}\n"
    with open(filepath, "w") as f:
        f.write(content)
    return filepath


class TestConvertScript(unittest.TestCase):
    """Tests for scripts/convert.sh."""

    def setUp(self) -> None:
        """Set up a temporary agency-agents-like repo structure."""
        self.tmpdir = tempfile.mkdtemp()
        # Create an engineering directory with agent files
        self.eng_dir = os.path.join(self.tmpdir, "engineering")
        os.makedirs(self.eng_dir)
        # Copy convert.sh into scripts/
        self.scripts_dir = os.path.join(self.tmpdir, "scripts")
        os.makedirs(self.scripts_dir)
        convert_src = os.path.join(SCRIPTS_DIR, "convert.sh")
        convert_dst = os.path.join(self.scripts_dir, "convert.sh")
        with open(convert_src, "r") as f:
            content = f.read()
        with open(convert_dst, "w") as f:
            f.write(content)
        os.chmod(convert_dst, 0o755)

    def _run_convert(self, *args: str) -> subprocess.CompletedProcess:
        """Run convert.sh with given arguments."""
        cmd = [os.path.join(self.scripts_dir, "convert.sh")] + list(args)
        return subprocess.run(
            cmd, capture_output=True, text=True, cwd=self.tmpdir
        )

    def test_converts_agent_to_copilot_format(self) -> None:
        """Agent .md files are converted to .agent.md with description
        frontmatter."""
        _create_agent_file(
            self.eng_dir, "test-agent.md",
            "Test Developer",
            "A test developer agent",
            "# Test Agent\n\nBody content here.",
        )
        result = self._run_convert("--tool", "copilot")
        self.assertEqual(result.returncode, 0)

        out_file = os.path.join(
            self.tmpdir, "integrations", "copilot", "agents",
            "test-developer.agent.md",
        )
        self.assertTrue(os.path.exists(out_file))

        with open(out_file, "r") as f:
            content = f.read()
        self.assertIn("description: A test developer agent", content)
        self.assertIn("# Test Agent", content)
        self.assertIn("Body content here.", content)
        # Should NOT contain color or name fields
        self.assertNotIn("color:", content)
        self.assertNotIn("name:", content)

    def test_skips_files_without_frontmatter(self) -> None:
        """Files without YAML frontmatter are skipped."""
        readme = os.path.join(self.eng_dir, "README.md")
        with open(readme, "w") as f:
            f.write("# Not an agent\nJust a readme.\n")

        result = self._run_convert("--tool", "copilot")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Converted 0 agents", result.stdout)

    def test_converts_multiple_agents(self) -> None:
        """Multiple agent files are all converted."""
        _create_agent_file(
            self.eng_dir, "agent-a.md", "Agent Alpha",
            "First agent", "Body A",
        )
        _create_agent_file(
            self.eng_dir, "agent-b.md", "Agent Beta",
            "Second agent", "Body B",
        )

        result = self._run_convert("--tool", "copilot")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Converted 2 agents", result.stdout)

        agents_dir = os.path.join(
            self.tmpdir, "integrations", "copilot", "agents"
        )
        files = sorted(os.listdir(agents_dir))
        self.assertEqual(files, [
            "agent-alpha.agent.md",
            "agent-beta.agent.md",
        ])

    def test_invalid_tool_fails(self) -> None:
        """An invalid --tool value causes a non-zero exit."""
        result = self._run_convert("--tool", "nonexistent")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown tool", result.stderr)

    def test_custom_output_directory(self) -> None:
        """The --out flag redirects output to a custom directory."""
        custom_out = os.path.join(self.tmpdir, "custom-out")
        _create_agent_file(
            self.eng_dir, "agent.md", "Custom Out",
            "Testing custom output", "Body",
        )
        result = self._run_convert("--tool", "copilot", "--out", custom_out)
        self.assertEqual(result.returncode, 0)

        out_file = os.path.join(
            custom_out, "copilot", "agents", "custom-out.agent.md"
        )
        self.assertTrue(os.path.exists(out_file))

    def test_help_flag(self) -> None:
        """The --help flag shows usage and exits cleanly."""
        result = self._run_convert("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage", result.stdout)
        self.assertIn("copilot", result.stdout)

    def test_slugifies_name_correctly(self) -> None:
        """Agent names are slugified to kebab-case for filenames."""
        _create_agent_file(
            self.eng_dir, "agent.md",
            "My  Special--Agent Name!",
            "Slug test", "Body",
        )
        result = self._run_convert("--tool", "copilot")
        self.assertEqual(result.returncode, 0)

        agents_dir = os.path.join(
            self.tmpdir, "integrations", "copilot", "agents"
        )
        files = os.listdir(agents_dir)
        self.assertEqual(len(files), 1)
        # Should be lowercase kebab-case, no double hyphens
        self.assertEqual(files[0], "my-special-agent-name.agent.md")

    def test_converts_agent_to_instructions_format(self) -> None:
        """Agent .md files are copied as-is for the instructions tool."""
        _create_agent_file(
            self.eng_dir, "test-agent.md",
            "Test Developer",
            "A test developer agent",
            "# Test Agent\n\nBody content here.",
        )
        result = self._run_convert("--tool", "instructions")
        self.assertEqual(result.returncode, 0)

        out_file = os.path.join(
            self.tmpdir, "integrations", "instructions",
            "test-agent.md",
        )
        self.assertTrue(os.path.exists(out_file))

        with open(out_file, "r") as f:
            content = f.read()
        # File is copied as-is — original frontmatter preserved
        self.assertIn("name: Test Developer", content)
        self.assertIn("description: A test developer agent", content)
        self.assertIn("# Test Agent", content)

    def test_converts_multiple_instructions(self) -> None:
        """Multiple agent files are all copied for the instructions tool."""
        _create_agent_file(
            self.eng_dir, "agent-a.md", "Agent Alpha",
            "First agent", "Body A",
        )
        _create_agent_file(
            self.eng_dir, "agent-b.md", "Agent Beta",
            "Second agent", "Body B",
        )

        result = self._run_convert("--tool", "instructions")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Converted 2 agents", result.stdout)

        out_dir = os.path.join(
            self.tmpdir, "integrations", "instructions"
        )
        files = sorted(os.listdir(out_dir))
        self.assertEqual(files, ["agent-a.md", "agent-b.md"])


class TestInstallScript(unittest.TestCase):
    """Tests for scripts/install.sh."""

    def setUp(self) -> None:
        """Set up a temporary repo with pre-converted copilot agents."""
        self.tmpdir = tempfile.mkdtemp()
        # Create integrations/copilot/agents/ with sample agent files
        self.agents_dir = os.path.join(
            self.tmpdir, "integrations", "copilot", "agents"
        )
        os.makedirs(self.agents_dir)
        # Create sample converted agent
        agent_content = (
            "---\n"
            "description: A test agent for installation\n"
            "---\n"
            "\n"
            "# Test Agent\n"
            "\n"
            "Body content.\n"
        )
        with open(
            os.path.join(self.agents_dir, "test-agent.agent.md"), "w"
        ) as f:
            f.write(agent_content)
        # Copy install.sh into scripts/
        self.scripts_dir = os.path.join(self.tmpdir, "scripts")
        os.makedirs(self.scripts_dir)
        install_src = os.path.join(SCRIPTS_DIR, "install.sh")
        install_dst = os.path.join(self.scripts_dir, "install.sh")
        with open(install_src, "r") as f:
            content = f.read()
        with open(install_dst, "w") as f:
            f.write(content)
        os.chmod(install_dst, 0o755)
        # Create a project directory to install into
        self.project_dir = tempfile.mkdtemp()

    def _run_install(self, *args: str) -> subprocess.CompletedProcess:
        """Run install.sh with given arguments from the project directory."""
        cmd = [os.path.join(self.scripts_dir, "install.sh")] + list(args)
        return subprocess.run(
            cmd, capture_output=True, text=True, cwd=self.project_dir
        )

    def test_installs_copilot_agents(self) -> None:
        """Agents are copied to .github/agents/ in the project."""
        result = self._run_install("--tool", "copilot")
        self.assertEqual(result.returncode, 0)

        installed = os.path.join(
            self.project_dir, ".github", "agents", "test-agent.agent.md"
        )
        self.assertTrue(os.path.exists(installed))

        with open(installed, "r") as f:
            content = f.read()
        self.assertIn("description: A test agent for installation", content)
        self.assertIn("# Test Agent", content)

    def test_installs_multiple_agents(self) -> None:
        """Multiple agents are all installed."""
        # Add a second agent
        with open(
            os.path.join(self.agents_dir, "second.agent.md"), "w"
        ) as f:
            f.write("---\ndescription: Second\n---\nBody\n")

        result = self._run_install("--tool", "copilot")
        self.assertEqual(result.returncode, 0)
        self.assertIn("2 agents", result.stdout)

        dest = os.path.join(self.project_dir, ".github", "agents")
        files = sorted(os.listdir(dest))
        self.assertEqual(files, ["second.agent.md", "test-agent.agent.md"])

    def test_fails_without_integrations(self) -> None:
        """Script fails gracefully when integrations/ is missing."""
        # Use a fresh temp dir as repo root (no integrations/)
        empty_dir = tempfile.mkdtemp()
        scripts = os.path.join(empty_dir, "scripts")
        os.makedirs(scripts)
        install_src = os.path.join(SCRIPTS_DIR, "install.sh")
        install_dst = os.path.join(scripts, "install.sh")
        with open(install_src, "r") as f:
            content = f.read()
        with open(install_dst, "w") as f:
            f.write(content)
        os.chmod(install_dst, 0o755)

        result = subprocess.run(
            [install_dst, "--tool", "copilot"],
            capture_output=True, text=True, cwd=self.project_dir,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("integrations/ not found", result.stderr)

    def test_invalid_tool_fails(self) -> None:
        """An invalid --tool value causes a non-zero exit."""
        result = self._run_install("--tool", "nonexistent")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown tool", result.stderr)

    def test_help_flag(self) -> None:
        """The --help flag shows usage and exits cleanly."""
        result = self._run_install("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage", result.stdout)
        self.assertIn("copilot", result.stdout)

    def test_creates_github_agents_directory(self) -> None:
        """The .github/agents/ directory is created if it does not exist."""
        dest = os.path.join(self.project_dir, ".github", "agents")
        self.assertFalse(os.path.exists(dest))

        result = self._run_install("--tool", "copilot")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(os.path.isdir(dest))

    def test_installs_instructions(self) -> None:
        """Instruction files are copied to .github/instructions/."""
        # Create integrations/instructions/ with a sample file
        inst_src = os.path.join(
            self.tmpdir, "integrations", "instructions"
        )
        os.makedirs(inst_src)
        with open(os.path.join(inst_src, "test-agent.md"), "w") as f:
            f.write(
                "---\nname: Test\ndescription: A test\n---\n\nBody.\n"
            )

        result = self._run_install("--tool", "instructions")
        self.assertEqual(result.returncode, 0)

        installed = os.path.join(
            self.project_dir, ".github", "instructions", "test-agent.md"
        )
        self.assertTrue(os.path.exists(installed))

        with open(installed, "r") as f:
            content = f.read()
        self.assertIn("name: Test", content)
        self.assertIn("Body.", content)

    def test_installs_multiple_instructions(self) -> None:
        """Multiple instruction files are all installed."""
        inst_src = os.path.join(
            self.tmpdir, "integrations", "instructions"
        )
        os.makedirs(inst_src)
        for name in ("first.md", "second.md"):
            with open(os.path.join(inst_src, name), "w") as f:
                f.write(f"---\nname: {name}\n---\nBody\n")

        result = self._run_install("--tool", "instructions")
        self.assertEqual(result.returncode, 0)
        self.assertIn("2 files", result.stdout)

        dest = os.path.join(
            self.project_dir, ".github", "instructions"
        )
        files = sorted(os.listdir(dest))
        self.assertEqual(files, ["first.md", "second.md"])

    def test_creates_github_instructions_directory(self) -> None:
        """The .github/instructions/ directory is created if missing."""
        inst_src = os.path.join(
            self.tmpdir, "integrations", "instructions"
        )
        os.makedirs(inst_src)
        with open(os.path.join(inst_src, "agent.md"), "w") as f:
            f.write("---\nname: Test\n---\nBody\n")

        dest = os.path.join(
            self.project_dir, ".github", "instructions"
        )
        self.assertFalse(os.path.exists(dest))

        result = self._run_install("--tool", "instructions")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(os.path.isdir(dest))


if __name__ == "__main__":
    unittest.main()
