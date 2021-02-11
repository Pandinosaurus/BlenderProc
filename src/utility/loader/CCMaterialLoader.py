import os

import bpy

from src.utility.MaterialLoaderUtility import MaterialLoaderUtility
from src.utility.Utility import Utility


class CCMaterialLoader:

    @staticmethod
    def load(folder_path: str = "resources/cctextures", used_assets: list = [], preload: bool = False, fill_used_empty_materials: bool = False, add_custom_properties: dict = {}):
        """ This method loads all textures obtained from https://cc0textures.com, use the script
        (scripts/download_cc_textures.py) to download all the textures to your pc.

        All textures here support Physically based rendering (PBR), which makes the textures more realistic.

        All materials will have the custom property "is_cc_texture": True, which will make the selection later on easier.

        :param folder_path: The path to the downloaded cc0textures.
        :param used_assets: A list of all asset names, you want to use. The asset-name must not be typed in completely, only the
                            beginning the name starts with. By default all assets will be loaded, specified by an empty list.
        :param preload: If set true, only the material names are loaded and not the complete material.
        :param fill_used_empty_materials: If set true, the preloaded materials, which are used are now loaded completely.
        :param add_custom_properties:  A dictionary of materials and the respective properties.
        """
        folder_path = Utility.resolve_path(folder_path)

        if preload and fill_used_empty_materials:
            raise Exception("Preload and fill used empty materials can not be done at the same time, check config!")

        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            for asset in os.listdir(folder_path):
                if used_assets:
                    skip_this_one = True
                    for used_asset in used_assets:
                        if asset.startswith(used_asset):
                            skip_this_one = False
                            break
                    if skip_this_one:
                        continue
                current_path = os.path.join(folder_path, asset)
                if os.path.isdir(current_path):
                    base_image_path = os.path.join(current_path, "{}_2K_Color.jpg".format(asset))
                    if not os.path.exists(base_image_path):
                        continue

                    # if the material was already created it only has to be searched
                    if fill_used_empty_materials:
                        new_mat = MaterialLoaderUtility.find_cc_material_by_name(asset, add_custom_properties)
                    else:
                        new_mat = MaterialLoaderUtility.create_new_cc_material(asset, add_custom_properties)
                    if preload:
                        # if preload then the material is only created but not filled
                        continue
                    elif fill_used_empty_materials and not MaterialLoaderUtility.is_material_used(new_mat):
                        # now only the materials, which have been used should be filled
                        continue

                    # construct all image paths
                    ambient_occlusion_image_path = base_image_path.replace("Color", "AmbientOcclusion")
                    metallic_image_path = base_image_path.replace("Color", "Metalness")
                    roughness_image_path = base_image_path.replace("Color", "Roughness")
                    alpha_image_path = base_image_path.replace("Color", "Opacity")
                    normal_image_path = base_image_path.replace("Color", "Normal")
                    displacement_image_path = base_image_path.replace("Color", "Displacement")

                    # create material based on these image paths
                    CCMaterialLoader.create_material(new_mat, base_image_path, ambient_occlusion_image_path,
                                                     metallic_image_path, roughness_image_path, alpha_image_path,
                                                     normal_image_path, displacement_image_path)
        else:
            raise Exception("The folder path does not exist: {}".format(folder_path))

    @staticmethod
    def create_material(new_mat: bpy.types.Material, base_image_path: str, ambient_occlusion_image_path: str, metallic_image_path: str,
                        roughness_image_path: str, alpha_image_path: str, normal_image_path: str, displacement_image_path: str):
        """
        Create a material for the cctexture datatset, the combination used here is calibrated to this.

        :param new_mat: The new material, which will get all the given textures
        :param base_image_path: The path to the color image
        :param ambient_occlusion_image_path: The path to the ambient occlusion image
        :param metallic_image_path: The path to the metallic image
        :param roughness_image_path: The path to the roughness image
        :param alpha_image_path: The path to the alpha image (when this was written there was no alpha image provided \
                                 in the haven dataset)
        :param normal_image_path: The path to the normal image
        :param displacement_image_path: The path to the displacement image
        """
        nodes = new_mat.node_tree.nodes
        links = new_mat.node_tree.links

        principled_bsdf = Utility.get_the_one_node_with_type(nodes, "BsdfPrincipled")
        output_node = Utility.get_the_one_node_with_type(nodes, "OutputMaterial")

        collection_of_texture_nodes = []
        base_color = MaterialLoaderUtility.add_base_color(nodes, links, base_image_path, principled_bsdf)
        collection_of_texture_nodes.append(base_color)

        principled_bsdf.inputs["Specular"].default_value = 0.333

        ao_node = MaterialLoaderUtility.add_ambient_occlusion(nodes, links, ambient_occlusion_image_path,
                                                              principled_bsdf, base_color)
        collection_of_texture_nodes.append(ao_node)

        metallic_node = MaterialLoaderUtility.add_metal(nodes, links, metallic_image_path,
                                                        principled_bsdf)
        collection_of_texture_nodes.append(metallic_node)

        roughness_node = MaterialLoaderUtility.add_roughness(nodes, links, roughness_image_path,
                                                             principled_bsdf)
        collection_of_texture_nodes.append(roughness_node)

        alpha_node = MaterialLoaderUtility.add_alpha(nodes, links, alpha_image_path, principled_bsdf)
        collection_of_texture_nodes.append(alpha_node)

        normal_node = MaterialLoaderUtility.add_normal(nodes, links, normal_image_path, principled_bsdf,
                                                       invert_y_channel=True)
        collection_of_texture_nodes.append(normal_node)

        displacement_node = MaterialLoaderUtility.add_displacement(nodes, links, displacement_image_path,
                                                                   output_node)
        collection_of_texture_nodes.append(displacement_node)

        collection_of_texture_nodes = [node for node in collection_of_texture_nodes if node is not None]

        MaterialLoaderUtility.connect_uv_maps(nodes, links, collection_of_texture_nodes)
