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
  ['/usr/share/syslinux/isohdpfx.bin',     # Gentoo
   '/usr/lib/ISOLINUX/isohdpfx.bin',       # Debian
   '/usr/lib/syslinux/bios/isohdpfx.bin',  # Arch
  ].each { |b| return b if File.exist?(b) }
  abort 'Error: Missing isohdpfx.bin from isolinux'
end

ISOLINUX = _set_isolinux

# Run checks for required files and binaries
def env_check
  %w(cpio sudo xorriso gzip find md5sum dd sync rm cp).each do |bin|
    abort "Error: requires #{bin} binary" unless system("which #{bin} >/dev/null")
  end
end

# Parse command line options
def parser
  parser = Trollop::Parser.new do
    banner <<-EOS
    Generator for mesa-jenkins installer

    Usage:
      make [options]
    where [options] are:
    EOS

    opt(:ia32, 'An i386 image', default: 'nil')
    opt(:x64, 'an x86-64 image', default: 'nil')
    opt(:filename, 'Where to save the generated iso', default: 'jenkins.iso')
    opt(:write_target, 'Write the iso to a drive if set', default: '/dev/null')
    opt(:debug, 'Run with debug prints', default: false)
    opt(:cleanup, 'cleanup after finishing', default: false)
    opt(:target_disk, 'the disk to install debian onto', default: 'sda')
  end

  opts = Trollop.with_standard_exception_handling(parser) do
    fail Trollop.HelpNeeded if ARGV.empty? # show help screen
    parser.parse ARGV
  end

  opts[:ia32] = nil if opts[:ia32] == 'nil'

  abort 'Error: x64 source required' if opts[:x64] == 'nil'

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

# Mount the cd images
def mount_cds(opts)
  FileUtils.mkdir('x64') unless Dir.exist?('x64')
  system("sudo mount -o loop #{opts[:x64]} x64 &>/dev/null") if Dir['x64/*'].empty?

  if opts[:ia32]
    FileUtils.mkdir('ia32') unless Dir.exist?('ia32')
    system("sudo mount -o loop #{opts[:ia32]} ia32 &>/dev/null") if Dir['ia32/*'].empty?
  end

  # Allow the mounts to settle
  sleep(1)

  abort "Error: #{opts[:x64]} image not mounted" if Dir['x64/*'].empty?
  abort "Error: #{opts[:ia32]} image not mounted" if opts[:ia32] && Dir['ia32/*'].empty?
end

# Copy the contents of the cd into the working directory
def copy_cd
  begin
    FileUtils.cp_r('x64/.', 'work')
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

  unless File.exist?("x64/install.amd/initrd.gz")
    abort 'Error: initrd.gz missing, is the source dir an image?'
  end

  FileUtils.mkdir('initrd')
  FileUtils.cd('initrd')

  out = opts[:debug] ? '' : '2>/dev/null'
  status = system('gzip -d < ../x64/install.amd/initrd.gz | '\
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
def update_initrd(opts)
  FileUtils.cp('jenkins.cfg', 'initrd/preseed.cfg')
  system("sed -i -e 's!<disk>!#{opts[:target_disk]}!g' initrd/preseed.cfg")
end

# Add finalize.sh to work
def add_finalize
  begin
    FileUtils.cp('finalize.sh', 'work')
  rescue Errno::EACCES
    abort 'Error: Could not copy finalize.sh to work directory'
  end
end

# Build a hybrid grub efi that can boot either ia32 or x64
def hybrid_grub(opts)
  return unless opts[:ia32]

  begin
    FileUtils.cp_r('ia32/boot/grub/i386-efi', 'work/boot/grub')
  rescue Errno::EACCES
    abort 'Error: Could not copy i386-efi directory to work directory'
  end

  # Create a new 100mb efi image, which will contain both x64 and ia32 images
  File.delete('efi.img') if File.exist?('efi.img')
  FileUtils.mkdir('efi_temp') unless Dir.exist?('efi_temp')

  command = 'sudo dd if=/dev/zero of=efi.img bs=1k count=100000'
  command += ' &>/dev/null' unless opts[:debug]
  system(command)

  command = 'sudo mkfs.vfat efi.img'
  command += ' &>/dev/null' unless opts[:debug]
  system(command)

  system('sudo mount -o loop efi.img efi_temp')
  system('sudo mkdir -p efi_temp/efi/boot')

  # Copy the efi images from both arches
  FileUtils.mkdir('temp') unless Dir.exist?('temp')
  %w(x64 ia32).each do |arch|
    system("sudo mount -o loop #{arch}/boot/grub/efi.img temp")
    system("sudo cp temp/efi/boot/boot#{arch}.efi efi_temp/efi/boot")
    system('sudo umount temp')
  end

  # Cleanup
  status = system('sudo umount efi_temp')
  abort 'Error: Temporary efi filesystem not unmounted' unless status == true
  FileUtils.rm_r('efi_temp')
  FileUtils.rm_r('temp')
end

# update bootloader configurations
def update_boot(opts)
  FileUtils.rm('work/isolinux/isolinux.cfg')
  FileUtils.cp('isolinux.cfg', 'work/isolinux')

  FileUtils.rm('work/boot/grub/grub.cfg')
  FileUtils.cp('grub.cfg', 'work/boot/grub')

  return unless opts[:ia32]

  FileUtils.rm('work/boot/grub/efi.img')
  FileUtils.cp('efi.img', 'work/boot/grub')
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
def cleanup(opts)
  system('sudo rm -rf initrd work')
  system('sudo umount x64')
  FileUtils.rm_r('x64')

  return unless opts[:ia32]

  system('sudo umount ia32')
  FileUtils.rm_r('ia32')
end

# Make the installer
def make_installer(opts)
  print 'Creating working directory... '
  make_workdir(opts)
  mount_cds(opts)
  copy_cd
  puts 'done'

  print 'Regenerating initrd image... '
  decompress_initrd(opts)
  update_initrd(opts)
  compress_initrd(opts)
  puts 'done'

  print 'Adding finalize.sh to installer... '
  add_finalize
  puts 'done'

  print 'Updating boot config... '
  hybrid_grub(opts)
  update_boot(opts)
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

  if opts[:cleanup]
    print 'Cleaning up temporary files... '
    cleanup(opts)
    puts 'done'
  else
    puts 'Cleanup disabled, not cleaning up temporary files'
  end
end

def main
  env_check
  make_installer(parser)
end

main if __FILE__ == $PROGRAM_NAME
