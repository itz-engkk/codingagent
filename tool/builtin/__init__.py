from tool.builtin.edit_file import EditTool
from tool.builtin.glob import GlobTool
from tool.builtin.grep import GrepTool
from tool.builtin.list_file import ListDirTool
from tool.builtin.memory import MemoryTool
from tool.builtin.readfile import ReadFileTool
from tool.builtin.shell import ShellTool
from tool.builtin.todo import TodosTool
from tool.builtin.webfetch import WebFetchTool
from tool.builtin.websearch import WebSearchTool
from tool.builtin.write_file import WriteFileTool
__all__ = [
    "ReadFileTool",
    "WriteFileTool",
    "EditTool",
    "ShellTool",
    "ListDirTool",
    "GrepTool",
    "GlobTool",
    "WebSearchTool",
    "WebFetchTool",
    "TodosTool",
    "MemoryTool",
    
    ]
def get_all_builtin_tools() -> list[type]:
    return [
        ReadFileTool,
        WriteFileTool,
        EditTool,
        ShellTool,
        ListDirTool,
        GrepTool,
        GlobTool,
        WebSearchTool,
        WebFetchTool,
        TodosTool,
        MemoryTool,
    ]