# ContBak 1.0.3

ContBak 1.0.3 fixes the Synology Docker host-path problem and introduces asynchronous backup jobs with a visible stage-based percentage display.

The percentage represents backup stages rather than compressed bytes, because the Alpine `tar` helper does not expose reliable byte progress.
