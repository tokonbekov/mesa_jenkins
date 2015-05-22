#!/usr/bin/ruby
# Copyright (c) 2015 Intel Corporation
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

require 'fileutils'
require 'trollop'

# Helper for setting the ISOLINUX constant
def _set_isolinux
  ['/usr/share/syslinux/isohdpfx.bin',
   '/usr/lib/ISOLINUX/isohdpfx.bin'].each { |b| return b if File.exist?(b) }
end

ISOLINUX = _set_isolinux

# Run checks for required files and binaries
def env_check
  %w(cpio sudo xorriso gzip find md5sum dd sync rm cp).each do |bin|
    abort "Error: requires #{bin} binary" unless system("which #{bin} >/dev/null")
  end
  abort 'Error: Missing isohdpfx.bin from isolinux' unless File.exist?(ISOLINUX)
end

# Parse command line options
def parser
  parser = Trollop::Parser.new do
    banner <<-EOS
    Generator for mesa-jenkins installer

    Usage:
      make [options] <source>
    where <source> is the contents of a debian installer
    where [options] are:
    EOS

    opt(:filename, 'Where to save the generated iso', default: 'jenkins.iso')
    opt(:write_target, 'Write the iso to a drive if set', default: '/dev/null')
    opt(:debug, 'Run with debug prints', default: false)
  end

  opts = Trollop.with_standard_exception_handling parser do
    fail Trollop.HelpNeeded if ARGV.empty? # show help screen
    parser.parse ARGV
  end

  abort 'Error: Only one source may be set' unless parser.leftovers.length == 1

  opts[:source] = parser.leftovers[0]

  opts
end

# Create a working directory
def make_workdir(opts)
  FileUtils.remove_dir('work', force: true) if Dir.exist?('work')

  begin
    FileUtils.mkdir('work')
  rescue Errno::EACCES
    abort 'Error: Cannot creates "work", permission denied'
  end
end

# Copy the contents of the cd into the working directory
def copy_cd(opts)
  unless Dir.exist?(opts[:source])
    abort "Error: No such directory #{opts[:source]}"
  end

  begin
    FileUtils.cp_r("#{opts[:source]}/.", 'work')
  rescue Errno::EACCES
    abort 'Error: permsission denied while writing to "work"'
  end
end

# Decompress initrd.gz and add preseed file
def decompress_initrd(opts)
  if Dir.exist?('initrd')
    status = system('sudo rm -rf initrd')
    abort 'Error: could not remove initrd folder' unless status == true
  end

  unless File.exist?("#{opts[:source]}/install.amd/initrd.gz")
    abort 'Error: initrd.gz missing, is the source dir an image?'
  end

  FileUtils.mkdir('initrd')
  FileUtils.cd('initrd')

  out = opts[:debug] ? '' : '2>/dev/null'
  status = system("gzip -d < ../#{opts[:source]}/install.amd/initrd.gz | "\
                  'sudo cpio --extract --make-directories '\
                  "--no-absolute-filenames #{out}")
  abort 'Error: could not decompress initrd.gz' unless status == true

  FileUtils.cd('..')
end

# recompress initrd.gz
def compress_initrd(opts)
  FileUtils.rm('work/install.amd/initrd.gz')
  FileUtils.cd('initrd')
  out = opts[:debug] ? '' : '2>/dev/null'
  status = system("find . | cpio -H newc --create #{out} |"\
                  'gzip -9 > ../work/install.amd/initrd.gz || exit 1')
  abort 'Error: Rebuilding initrd failed' unless status == true
  FileUtils.cd('..')
  FileUtils.chmod(0444, 'work/install.amd/initrd.gz')
end

# add files to initrd
def update_initrd
  FileUtils.cp('jenkins.cfg', 'initrd/preseed.cfg')
end

# Add finalize.sh to work
def add_finalize
  begin
    FileUtils.cp('finalize.sh', 'work')
  rescue Errno::EACCES
    abort 'Error: Could not copy finalize.sh to work directory'
  end
end

# update bootloader configurations
def update_boot
  FileUtils.rm('work/isolinux/isolinux.cfg')
  FileUtils.cp('isolinux.cfg', 'work/isolinux')

  FileUtils.rm('work/boot/grub/grub.cfg')
  FileUtils.cp('grub.cfg', 'work/boot/grub')
end

# Regenerate md5 sums
def make_md5(opts)
  FileUtils.cd('work')

  FileUtils.chmod('+w', 'md5sum.txt') if File.exist?('md5sum.txt')

  out = opts[:debug] ? '' : '2>/dev/null'
  status = system('md5sum `find ! -name "md5sum.txt" ! '\
                  "-path './isolinx/*' -follow -type f #{out} || "\
                  "exit 1` > md5sum.txt #{out}")
  abort 'Error: unable to regenerate md5sums' unless status == true

  FileUtils.chmod('-w', 'md5sum.txt')

  FileUtils.cd('..')
end

# Generate the iso file
def make_iso(opts)
  # -no-emul-boot is in there twice. This is required to make things work
  command = 'xorriso '\
            '-as mkisofs '\
            '-graft-points '\
            '-V "JENKINS_DEBIAN" '\
            '-A "Debian Jenkins Installer" '\
            '-J '\
            '-r '\
            '-boot-load-size 4 '\
            '-boot-info-table '\
            '-no-emul-boot '\
            '-b isolinux/isolinux.bin '\
            '-c isolinux/boot.cat '\
            "-isohybrid-mbr #{ISOLINUX} "\
            '-eltorito-alt-boot '\
            '-e boot/grub/efi.img '\
            '-no-emul-boot '\
            '-isohybrid-gpt-basdat '\
            "-o #{opts[:filename]} "\
            './work'
  command += ' &>/dev/null' unless opts[:debug]

  status = system(command)
  abort 'Error: ISO not created successfully' unless status == true

  system('sync')
end

# Write the iso as an image
def write_image(opts)
  command = "sudo dd if=#{opts[:filename]} of=#{opts[:write_target]} bs=4k"
  command += ' &>/dev/null' unless opts[:debug]
  status = system(command)
  abort "Error: could not write to #{opts[:write_target]}" unless status == true
end

# Cleanup working directories
def cleanup
  system('sudo rm -rf initrd work')
end

# Make the installer
def make_installer(opts)
  print 'Creating working directory... '
  make_workdir(opts)
  copy_cd(opts)
  puts 'done'

  print 'Regenerateing initrd image... '
  decompress_initrd(opts)
  update_initrd
  compress_initrd(opts)
  puts 'done'

  print 'Adding finalize.sh to installer... '
  add_finalize
  puts 'done'

  print 'Updating boot config... '
  update_boot
  puts 'done'

  print 'Regenerating md5sums... '
  make_md5(opts)
  puts 'done'

  print 'Building iso image... '
  make_iso(opts)
  puts 'done'

  if opts[:write_target] != '/dev/null'
    print "Writing to disk #{opts[:write_target]}... "
    write_image(opts)
    puts 'done'
  else
    puts 'No write target specified, not writing to disk'
  end

  if opts[:debug] == false
    print 'Cleaning up temporary files... '
    cleanup
    puts 'done'
  else
    puts 'Debug enabled, not cleaning up temporary files'
  end
end

def main
  env_check
  make_installer(parser)
end

main if __FILE__ == $PROGRAM_NAME
