# pyfusezip

Mounts a ZIP archive as a filesystem via FUSE. Read-only support. Alpha-quality (one afternoon of work). See *See Also* and *Why?* as well. Needs the FUSE Python package, e.g. `apt install python3-fuse` under Ubuntu.

## Usage

``` 
pyfusezip zipfile.zip ~/mnt
```

## License

MIT

## See Also

More feature complete and mature tools exist for this task, see *e.g.*, [archivemount](https://github.com/cybernoid/archivemount/) or [fuse-zip](https://bitbucket.org/agalanin/fuse-zip).

## Why?

I had some large ZIP files (either many files or large overall size) I wanted to transparently work with, without decompressing them completely first. I thought the situation was pretty much solved, till I tried the existing FUSE-based tools. To my surprise, either it took longer than I was willing to wait to mount, and/or read performance was low.

These benchmarks were done quickly to get an idea how the different tools compare. I do not claim them to be perfectly accurate.

### First Benchmark – Mount and list many files

Mounting and iterating over files in a 159 GB / 89542 files ZIP file:

```bash
# Baseline. zipinfo ... takes around a second
> sync; drop_caches; time ( timeout 60 zipinfo large.zip | wc -l )
89545
( timeout 60 zipinfo large.zip | wc -l; )  0.77s user 1.04s system 173% cpu 1.049 total

# pyfusezip. Mount and find to list all files take around 3.5s
> sync; drop_caches; time ( timeout 60 pyfusezip large.zip ~/mnt; find ~/mnt | wc -l ); fusermount -u ~/mnt
89547
( timeout 60 pyfusezip ~/mnt; find w)  0.94s user 0.97s system 54% cpu 3.519 total

# archivemount. What I tried initially, I was too impatient to wait for it to complete ... no result within a minute
> sync; drop_caches; time ( timeout 60 archivemount large.zip ~/mnt; find ~/mnt | wc -l ); fusermount -u ~/mnt                            
1
( timeout 60 archivemount large.zip ~/mnt; fin)  0.41s user 1.65s system 3% cpu 1:00.02 total
fusermount: entry for ~/mnt not found in /etc/mtab

# fuze-zip. Does not yield a result within a minute either.
> sync; drop_caches; time ( timeout 60 fuse-zip large.zip ~/mnt; find ~/mnt | wc -l ); fusermount -u ~/mnt
1
( timeout 60 fuse-zip large.zip ~/mnt; find  |)  0.41s user 1.52s system 3% cpu 1:00.02 total
fusermount: entry for ~/mnt not found in /etc/mtab
```

**Result:** For ZIP files containing many files, the mount and traverse performance is unexpectedly bad for the other, compiled tools

*Note*: The [drop_caches](https://github.com/csachs/drop_caches) utility writes 3 to `/proc/sys/vm/drop_caches` to clear kernel caches, *i.e.*, filesystem caches as well.

### Second Benchmark – Mount and list few files

In order to get some numbers, another test with mounting a smaller ZIP file. The ZIP file is 19 GB and has 37 files.

```bash
# Baseline. zipinfo ... 8ms
sync; drop_caches; time ( timeout 60 zipinfo small.zip | wc -l )
40
( timeout 60 zipinfo small.zip | wc -l; )  0.00s user 0.01s system 137% cpu 0.008 total

# pyfusezip. Mount and find to list all files take around 64ms
sync; drop_caches; time ( timeout 60 pyfusezip small.zip ~/mnt; find ~/mnt | wc -l ); fusermount -u ~/mnt
40
( timeout 60 pyfusezip ~/mnt; find w)  0.04s user 0.02s system 92% cpu 0.064 total

# archivemount. For a smaller archive it works fast with 24ms
sync; drop_caches; time ( timeout 60 archivemount small.zip ~/mnt; find ~/mnt | wc -l ); fusermount -u ~/mnt
40
( timeout 60 archivemount small.zip ~/mnt; find ~/mnt | )  0.01s user 0.01s system 72% cpu 0.024 total

# fuze-zip. For a smaller archive it works fast with 27ms
sync; drop_caches; time ( timeout 60 fuse-zip small.zip ~/mnt; find ~/mnt | wc -l ); fusermount -u ~/mnt
40
( timeout 60 fuse-zip small.zip ~/mnt; find ~/mnt | wc -)  0.00s user 0.01s system 68% cpu 0.027 total
```

**Result:** For ZIP files containing few files, the mount and traverse performance is expectedly better for the other, compiled tools.

### Third Benchmark – Read large files

Again the smaller archive, this time reading a (2.5 GB) file from it:

```bash
> pyfusezip small.zip ~/mnt
> drop_caches; dd if=$HOME/mnt/large_file of=/dev/null bs=512 count=1000
# 512000 bytes (512 kB. 500 KiB) copied. 0.0295627 s. 17.3 MB/s
> drop_caches; dd if=$HOME/mnt/large_file of=/dev/null bs=512 count=10000
# 5120000 bytes (5.1 MB. 4.9 MiB) copied. 0.0389242 s. 132 MB/s
> drop_caches; dd if=$HOME/mnt/large_file of=/dev/null bs=512 count=50000
# 25600000 bytes (26 MB. 24 MiB) copied. 0.0904043 s. 283 MB/s
> drop_caches; dd if=$HOME/mnt/large_file of=/dev/null
# 2621746032 bytes (2.6 GB. 2.4 GiB) copied. 11.5513 s. 227 MB/s
> fusermount -u ~/mnt

> archivemount small.zip ~/mnt
> drop_caches; dd if=$HOME/mnt/large_file of=/dev/null bs=512 count=1000
# 512000 bytes (512 kB. 500 KiB) copied. 0.0233606 s. 21.9 MB/s
> drop_caches; dd if=$HOME/mnt/large_file of=/dev/null bs=512 count=10000
# 5120000 bytes (5.1 MB. 4.9 MiB) copied. 0.252552 s. 20.3 MB/s
> drop_caches; dd if=$HOME/mnt/large_file of=/dev/null bs=512 count=50000
# 25600000 bytes (26 MB. 24 MiB) copied. 3.85426 s. 6.6 MB/s
# no whole test. I don't want to wait
> fusermount -u ~/mnt

> fuse-zip small.zip ~/mnt
> drop_caches; dd if=$HOME/mnt/large_file of=/dev/null bs=512 count=1000
# 512000 bytes (512 kB. 500 KiB) copied. 0.00558354 s. 91.7 MB/s
> drop_caches; dd if=$HOME/mnt/large_file of=/dev/null bs=512 count=10000
# 5120000 bytes (5.1 MB. 4.9 MiB) copied. 0.0265216 s. 193 MB/s
> drop_caches; dd if=$HOME/mnt/large_file of=/dev/null bs=512 count=50000
# 25600000 bytes (26 MB. 24 MiB) copied. 0.0784955 s. 326 MB/s
> drop_caches; dd if=$HOME/mnt/large_file of=/dev/null
# 2621746032 bytes (2.6 GB. 2.4 GiB) copied. 6.32691 s. 414 MB/s
> fusermount -u ~/mnt
```

**Result**: fuse-zip delivers the best performance, followed by pyfusezip. archivemount is weirdly slow, with its performance degrading as one progresses thru a large file. It should be noted however, that fuse-zip seems to unpack the whole file into memory, as its memory usage climbs during the read, something which might be prohibitive if the file is  larger than the available memory.
