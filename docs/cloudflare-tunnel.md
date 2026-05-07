# A Friendly Introduction to Cloudflare Tunnel

If you have ever built something on your laptop and wished, just for a
moment, that you could show it to a friend across town — or, more often,
test it on the small computer in your pocket — this guide is for you. We
are going to walk through a tool called **Cloudflare Tunnel**, and by the
end you will have a public, secure web address that points at the project
running on your own machine. No router settings to change, no domain to
buy, no certificates to wrestle with.

Take your time. None of this is hard, and we will explain *why* each piece
exists rather than only telling you to type it.

---

## Why your laptop is hard to reach from the outside world

When you start a development server, your project usually announces itself
at an address like `http://localhost:3000`. The word *localhost* is a
friendly nickname your computer uses for itself: it means "right here, on
this machine." Type that address into a browser on the same laptop and the
page loads. Try it from your phone, and nothing happens. The phone has no
idea what *localhost* means — to your phone, *localhost* is the phone.

You might already know there is a slightly cleverer trick: most home
networks let devices on the same Wi-Fi find each other by an internal
address that looks like `192.168.1.42` or similar. If you discover your
laptop's address and type `http://192.168.1.42:3000` into your phone, the
page often *does* load. Problem solved? Not quite.

Modern browsers, especially on iPhones, have grown careful about pages
served over plain `http://`. They consider those pages **insecure** and
quietly disable a long list of features when they encounter one — your
page can no longer ask for the user's location, can no longer use the
clipboard, can no longer install a service worker, and on iOS Safari it
operates under tighter memory limits that have, in real projects, caused
otherwise innocent pages to crash. To unlock the full browser, your page
has to arrive over `https://`. And acquiring a real `https://` address for
a laptop, traditionally, has been a small adventure involving DNS records,
certificates, and firewall rules.

Cloudflare Tunnel removes that adventure.

---

## What a "quick tunnel" actually is

Imagine your laptop and a stranger's phone are at opposite ends of a long
hallway with a locked door in the middle. The phone cannot push the door
open from its side. But your laptop, from its side, *can* — it can open
the door, walk through, and hand a string out into the hallway. Anyone in
the hallway can grab the string, give it a tug, and a message travels
back through the doorway to your laptop.

A Cloudflare quick tunnel works that way. A small program called
`cloudflared`, running on your laptop, opens an outbound connection to
Cloudflare's network — outbound, like making a phone call, which firewalls
and home routers happily allow. Cloudflare hands back a freshly minted web
address (something like `https://breezy-otter-paint.trycloudflare.com`)
that already lives behind their wildcard certificate, so every browser on
Earth trusts it instantly. When someone visits that address, the request
travels into Cloudflare's edge network, slips back down the connection
your laptop opened, and arrives at your project as if the visitor were
sitting at your keyboard.

```
Phone or remote browser
         │  https
         ▼
https://<random>.trycloudflare.com   ← Cloudflare assigns this, with a real TLS cert
         │
         │   (Cloudflare's global network)
         │
         ▼
cloudflared, running on your laptop
         │  http
         ▼
http://localhost:80     ← your project, where Caddy is already listening
```

The "quick" in *quick tunnel* is meant literally. There is no account to
create, no domain to register, no configuration file to write. You run
one command, copy the address it prints, and you are done.

There is, of course, a tradeoff for that simplicity, and we will return
to it.

---

## What you will need

This guide assumes:

- You have the WaterPulse project running with Docker Compose
  (`docker compose up -d`), which means Caddy — the small reverse proxy
  that fronts the whole stack — is listening on port 80 of your laptop.
- You are on Windows 11. The same ideas apply to macOS and Linux, but
  the install commands differ slightly.

That is honestly the entire prerequisite list. Cloudflare Tunnel does
not need a domain, an account, or special permissions on your network.

### Installing the `cloudflared` program

`cloudflared` is the small companion program that opens the tunnel. On
Windows, the friendliest way to install it is with `winget`, the package
manager that ships with modern Windows:

```bash
winget install --id Cloudflare.cloudflared --accept-package-agreements --accept-source-agreements
```

When the installer finishes, the program lives at
`C:\Program Files (x86)\cloudflared\cloudflared.exe`. One small surprise:
the installer does not always teach your *current* terminal where to
find it. Either close that terminal and open a fresh one, or use the
full path to the program in your commands — both are shown below.

A quick check that everything is in order:

```bash
"/c/Program Files (x86)/cloudflared/cloudflared.exe" --version
```

You should see a line like `cloudflared version 2025.8.1`. If you see an
error instead, the installer did not finish, or you need a fresh
terminal.

---

## Opening your first tunnel

Here is the entire incantation:

```bash
"/c/Program Files (x86)/cloudflared/cloudflared.exe" tunnel --url http://localhost:80
```

Read that command out loud and it almost explains itself: *please open
a tunnel, and route traffic to the address `http://localhost:80`.* That
address is where Caddy is listening on your laptop, and Caddy already
knows how to send the request along to the frontend, the backend, or
the map tiles depending on the path.

If you have added `cloudflared` to your `PATH`, the shorter form works:

```bash
cloudflared tunnel --url http://localhost:80
```

The program will print a flurry of lines as it dials home and shakes
hands with Cloudflare's network. After a few seconds, the line you
care about appears:

```
INF Your quick Tunnel has been created! Visit it at:
INF https://surplus-takes-weekend-leone.trycloudflare.com
INF Registered tunnel connection
```

That second line is your address. Copy it, type it into your phone's
browser, and the application loads — over `https://`, with a green
padlock, on a hostname your phone has never heard of, all without
touching your router. The first time you see this work, it feels a
little like magic.

### A gentle smoke test

Before you go hunting for bugs on the phone, it is worth confirming the
tunnel is delivering what you expect. From your laptop:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://<your-subdomain>.trycloudflare.com/
curl -s -o /dev/null -w "%{http_code}\n" https://<your-subdomain>.trycloudflare.com/api/auth/me
curl -s -o /dev/null -w "%{http_code}\n" -I https://<your-subdomain>.trycloudflare.com/tiles/canada.pmtiles
```

You are looking for three numbers in this order: `200`, `401`, `200`.
Translated into English: the home page loaded, the backend is reachable
and correctly told you that you are not logged in, and the basemap file
is being served. Three green lights, ready to go.

---

## Living with a running tunnel

The tunnel exists for exactly as long as the `cloudflared` program is
running. Close the terminal, put your laptop to sleep, switch VPNs, lose
internet for a long minute — any of those will end the tunnel, and the
next one you open will have a different address. This is not a bug; it
is the contract a quick tunnel offers in exchange for being free and
configuration-free.

You have two reasonable ways to keep the program running:

- **Leave it in a terminal.** The simplest, most honest option. The
  terminal becomes the tunnel's home, and pressing Ctrl+C closes it
  cleanly when you are done.
- **Run it in the background and write its logs to a file.** Useful
  when you want your terminal back. From a Bash shell:
  ```bash
  cloudflared tunnel --url http://localhost:80 > tunnel.log 2>&1 &
  tail -f tunnel.log
  ```
  The first command starts the tunnel and quietly redirects its output
  to a file. The second prints the file as it grows, so you can watch
  for the public address.

When you are finished, stopping the tunnel is the inverse of starting
it. In the foreground, press Ctrl+C. In the background, find the
process and end it:

```bash
tasklist //FI "IMAGENAME eq cloudflared.exe"
taskkill //F //IM cloudflared.exe
```

---

## When something is not quite right

Most of the time, the tunnel either works on the first try or fails in
a way that is easy to diagnose. Here are the situations that come up
most often, and what they usually mean.

If you visit the address and see a Cloudflare-branded error page (a
"1033" or "502" or similar number), the tunnel itself is fine but the
laptop end is not yet ready. Either `cloudflared` is still finishing
its handshake — wait fifteen seconds — or the local stack is not
running. A quick `curl -I http://localhost/` from the laptop will tell
you which.

If the page loads but every API call returns a 404, the frontend was
built at some earlier moment with the wrong API address baked into it.
Rebuild it:

```bash
docker compose up -d --build frontend
```

If the map page loads but the basemap is blank — the tile file is
missing, or the environment variable that points to it is empty. Check
that `tiles/canada.pmtiles` exists and that `NEXT_PUBLIC_TILES_URL` is
set in your `.env`.

If a tunnel that was working for hours suddenly drops, the most likely
cause is a hiccup somewhere along the path — your home internet, your
ISP, or the particular Cloudflare edge node you happened to land on
cycling. Restart `cloudflared` and continue with the new address.

A small, friendly clarification on cookies: in your `.env`, the
variable `COOKIE_SECURE=False` is correct for local development. The
cookie still travels over Cloudflare's HTTPS leg of the journey — what
the variable controls is whether the cookie itself carries the
`Secure` flag, which would cause the browser to drop it on the
laptop's plain-`http://` leg. For tunnel testing, leave it off.

---

## When you outgrow a quick tunnel

Quick tunnels are perfect for the moment you are in: a few minutes or
hours of testing, a teammate looking at your screen-share, a phone you
want to verify a layout on. They are not the right tool when you need
the *same* address to keep working tomorrow, or when you want to hand
something to a stakeholder for a week of feedback.

For those situations, Cloudflare offers a more grown-up cousin called
a **named tunnel**. It is a little more setup — a free Cloudflare
account, a domain on Cloudflare DNS, and a small configuration file —
but in exchange, the tunnel hostname becomes yours and stays the same
across restarts. The shape of the setup looks like this:

```bash
cloudflared tunnel login                                  # opens the browser
cloudflared tunnel create waterpulse-dev                  # creates the tunnel
cloudflared tunnel route dns waterpulse-dev dev.example.ca   # adds a DNS record
# write a small config.yml mapping ingress rules → localhost:80
cloudflared tunnel run waterpulse-dev
```

That is the door at the top of the staircase. If you walk all the way
up, you reach the actual production deployment described in
[CLAUDE_infrastructure.md](../CLAUDE_infrastructure.md), where the
project lives on a real server with its own real domain and Caddy
provisions a real Let's Encrypt certificate.

But that is a story for another chapter. For today, the quick tunnel
is more than enough — and once you have used it a few times, you will
find yourself reaching for it any time you want a real device to see
what you are working on.
