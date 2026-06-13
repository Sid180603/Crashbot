"""
Unit tests for crash parser
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.parsers.crash_parser import WinDbgParser


@pytest.mark.unit
@pytest.mark.parser
def test_parser_initialization(temp_dump_file):
    """Test parser initialization"""
    parser = WinDbgParser(temp_dump_file)
    assert parser.dump_path == temp_dump_file
    assert parser.timeout > 0


@pytest.mark.unit
@pytest.mark.parser
@patch('subprocess.run')
def test_run_cdb_command_success(mock_run, temp_dump_file):
    """Test running CDB command successfully"""
    # Mock subprocess output
    mock_run.return_value = Mock(
        returncode=0,
        stdout="CDB output here",
        stderr=""
    )
    
    parser = WinDbgParser(temp_dump_file)
    result = parser._run_cdb_command([".ecxr", "k"])
    
    assert result is not None
    mock_run.assert_called_once()


@pytest.mark.unit
@pytest.mark.parser
@patch('subprocess.run')
def test_run_cdb_command_timeout(mock_run, temp_dump_file):
    """Test CDB command timeout"""
    mock_run.side_effect = TimeoutError("Command timed out")
    
    parser = WinDbgParser(temp_dump_file)
    
    with pytest.raises(TimeoutError):
        parser._run_cdb_command([".ecxr"])


@pytest.mark.unit
@pytest.mark.parser
def test_extract_exception_info():
    """Test exception info extraction from CDB output"""
    parser = WinDbgParser("dummy.dmp")
    cdb_output = """
    ExceptionCode: c0000005 (Access violation)
    ExceptionAddress: 0000000000401234
    """
    
    exception_code = parser._extract_exception_code(cdb_output)
    assert exception_code == "0xC0000005"


@pytest.mark.unit
@pytest.mark.parser
def test_parse_stack_trace():
    """Test stack trace parsing"""
    parser = WinDbgParser("dummy.dmp")
    stack_output = """
    00 00000000`00401234 myapp!main+0x34
    01 00000000`77001234 ntdll!RtlUserThreadStart+0x21
    """
    
    frames = parser._parse_stack_trace(stack_output)
    assert len(frames) >= 2
    assert frames[0]["module"] == "myapp"
    assert frames[0]["function"] == "main"


@pytest.mark.unit
@pytest.mark.parser
def test_parse_loaded_modules():
    """Test loaded modules parsing"""
    parser = WinDbgParser("dummy.dmp")
    module_output = """
    00400000 00410000   myapp      (deferred)
    77000000 77200000   ntdll      (pdb symbols)
    """
    
    modules = parser._parse_loaded_modules(module_output)
    assert len(modules) >= 2
    assert any(m["name"] == "myapp" for m in modules)


@pytest.mark.integration
@pytest.mark.parser
def test_parse_real_dump(temp_dump_file):
    """Integration test with real WinDbg (requires WinDbg installed)"""
    import os
    from app.core.config import settings
    
    # Check if WinDbg is available
    if not os.path.exists(settings.WINDBG_PATH):
        pytest.skip("WinDbg not installed")
    
    parser = WinDbgParser(temp_dump_file)
    
    # This will fail with mock dump file, but tests the full flow
    with pytest.raises(Exception):
        parser.parse()


@pytest.mark.unit
@pytest.mark.parser
def test_parse_with_invalid_dump(temp_dump_file):
    """Test parser with invalid dump file"""
    parser = WinDbgParser(temp_dump_file)
    
    # Should handle gracefully or raise appropriate error
    # Implementation depends on error handling strategy
    result = parser.parse()
    assert "error" in result or "exception_code" in result
