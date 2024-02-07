#!/usr/bin/env python3
import subprocess
import argparse
import utils
import rospkg
import os


def main():

    # Parse arguments
    parser = argparse.ArgumentParser(description='Spawn px4 controller for SITL')
    parser.add_argument('-model', type=str, default="mbzirc",
                        help='robot model name, must match xacro description folder name') #TBD: px4 default models compatibility
    parser.add_argument('-estimator', type=str, default="ekf2",
                        help='estimator to use')
    parser.add_argument('-id', type=int, default=1,
                        help='robot id, used to compute udp ports')
    parser.add_argument('-description_package', type=str, default="robots_description",
                        help='robot description package, must follow robots_description file structure')
    args, unknown = parser.parse_known_args()
    utils.check_unknown_args(unknown)

    # Get an instance of RosPack with the default search paths
    rospack = rospkg.RosPack()

    # Create temporary directory for robot sitl stuff
    temp_dir = utils.temp_dir(args.id)
    subprocess.call("rm -rf " + temp_dir + "/rootfs", shell=True)
    subprocess.call("mkdir -p " + temp_dir + "/rootfs", shell=True)

    # Get udp configuration, depending on id
    udp_config = utils.udp_config(args.id)

    # Modify commands file to fit robot ports
    commands_file = rospack.get_path(args.description_package) + "/models/" + args.model + "/px4cmd"
    modified_cmds = temp_dir + "/rootfs/cmds"

    # Create symlink to the PX4 command file
    rp_list = rospack.list()
    
    gz_env = os.environ.copy()
    print("------------------Hello mate-------------------")
    
    if 'px4' not in rp_list:
        print("px4 not found in ROS_PACKAGE_PATH from run_px4sitl.py")
        # Try to export it to ROS_PACKAGE_PATH 
        
        # find PX4-Autopilot directory recursively
        for root, dirs, files in os.walk('/home/'):
            if 'PX4-Autopilot' in dirs:
                px4_src = os.path.abspath(os.path.join(root, 'PX4-Autopilot'))
                print("PX4-Autopilot found in " + px4_src)
                gz_env['ROS_PACKAGE_PATH'] += ':' + px4_src + ':' + px4_src + '/Tools/simulation/gazebo-classic/sitl_gazebo-classic'
                break
        #TBD: errors management

    
    
    #Study from here:
    
    custom_model_name = "custom_" + args.model
    px4_commands_dst = px4_src + "/ROMFS/px4fmu_common/init.d-posix/airframes/" + str(hash(custom_model_name) % 10**8) + "_" + custom_model_name
    subprocess.call("ln -sf " + commands_file + " " + px4_commands_dst, shell=True)
    
    print(commands_file)
    print(px4_commands_dst)
    
    if os.path.exists(commands_file + '.post'):
        subprocess.call("ln -sf " + commands_file + ".post " + px4_commands_dst + ".post", shell=True)

    # Set PX4 environment variables
    px4_env = os.environ.copy()
    px4_env['PX4_SIM_MODEL'] = custom_model_name
    px4_env['PX4_ESTIMATOR'] = args.estimator

    # Spawn px4
    px4_bin = px4_src + "/build/px4_sitl_default/bin/px4" # still existing
    px4_rootfs = px4_src + "/ROMFS/px4fmu_common" # still existing too
    rcs_file = "etc/init.d-posix/rcS"
    px4_args = px4_bin + " " + px4_rootfs + " -s " + rcs_file + " -i " + str(args.id-1) + " -w " + temp_dir + "/rootfs"
    px4_out = open(temp_dir+"/px4.out", 'w')
    px4_err = open(temp_dir+"/px4.err", 'w')
    px4 = subprocess.Popen(px4_args, env=px4_env, shell=True, stdout=px4_out, stderr=px4_err, cwd=temp_dir)

    # Wait for it!
    try:
        px4.wait()
    except KeyboardInterrupt:
        pass
    finally:
        px4_out.close()
        px4_err.close()


if __name__ == "__main__":
    main()
