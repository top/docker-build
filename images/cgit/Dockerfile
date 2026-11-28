FROM alpine:latest

RUN apk add --no-cache \
        cgit \
        git \
        git-daemon \
        lighttpd \
        highlight \
    && mkdir -p /srv/git /var/cache/cgit /run/lighttpd \
    && sed -i 's/exec highlight --force -f -I -X/exec highlight --force -f -I -O xhtml/' /usr/lib/cgit/filters/syntax-highlighting.sh \
    && cat <<'EOF' >> /usr/share/webapps/cgit/cgit.css

/* Syntax highlighting styles for highlight v3/v4 (.hl.*) and v2 */
table.blob .num, table.blob .hl.num { color:#b07e00; }
table.blob .esc, table.blob .hl.esc { color:#ff00ff; }
table.blob .str, table.blob .hl.str, table.blob .hl.sng { color:#bf0303; }
table.blob .dstr, table.blob .hl.dstr { color:#818100; }
table.blob .slc, table.blob .hl.slc { color:#838183; font-style:italic; }
table.blob .com, table.blob .hl.com { color:#838183; font-style:italic; }
table.blob .dir, table.blob .hl.dir, table.blob .hl.ppc { color:#008200; }
table.blob .sym, table.blob .hl.sym, table.blob .hl.opt { color:#000000; }
table.blob .kwa, table.blob .hl.kwa { color:#000000; font-weight:bold; }
table.blob .kwb, table.blob .hl.kwb { color:#0057ae; }
table.blob .kwc, table.blob .hl.kwc { color:#000000; font-weight:bold; }
table.blob .kwd, table.blob .hl.kwd { color:#010181; }
@media only all and (prefers-color-scheme: dark) {
    table.blob .num, table.blob .hl.num { color:#ff814f; }
    table.blob .esc, table.blob .hl.esc { color:#f60; }
    table.blob .str, table.blob .hl.str, table.blob .hl.sng { color:#cc0; }
    table.blob .dstr, table.blob .hl.dstr { color:#ffff7e; }
    table.blob .slc, table.blob .hl.slc { color:#7f7c7f; }
    table.blob .com, table.blob .hl.com { color:#7e7c7e; }
    table.blob .dir, table.blob .hl.dir, table.blob .hl.ppc { color:#7dff7d; }
    table.blob .sym, table.blob .hl.sym, table.blob .hl.opt { color:#eeeeee; }
    table.blob .kwa, table.blob .hl.kwa { color:#bb0; }
    table.blob .kwb, table.blob .hl.kwb { color:#0a0; }
    table.blob .kwc, table.blob .hl.kwc { color:#eeeeee; }
    table.blob .kwd, table.blob .hl.kwd { color:#7e7efe; }
}
EOF

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80
VOLUME ["/srv/git"]

ENTRYPOINT ["/entrypoint.sh"]
