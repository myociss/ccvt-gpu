#include <CGAL/Simple_cartesian.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/Heat_method_3/Surface_mesh_geodesic_distances_3.h>
#include <fstream>
#include <iostream>

#include <boost/foreach.hpp>

typedef CGAL::Simple_cartesian<double>                       Kernel;
typedef Kernel::Point_3                                      Point_3;
typedef CGAL::Surface_mesh<Point_3>                          Triangle_mesh;

typedef boost::graph_traits<Triangle_mesh>::vertex_descriptor vertex_descriptor;
typedef Triangle_mesh::Property_map<vertex_descriptor,double> Vertex_distance_map;
typedef CGAL::Heat_method_3::Surface_mesh_geodesic_distances_3<Triangle_mesh> Heat_method;


std::vector<std::array<double, 2>> computeVoronoi(std::vector<int> seeds, Triangle_mesh tm, Vertex_distance_map vertex_distance, Heat_method hm){
  std::vector<std::array<double, 2>> distances;

  BOOST_FOREACH(vertex_descriptor vd , vertices(tm)){
    distances.push_back({0.0,0.0});
  }
  

  for(int i=0; i < seeds.size(); i++){
    //get random vertices to use as seeds
    //int num = (rand() % (upper + 1));
    vertex_descriptor(source) = *(vertices(tm).begin() + seeds[i]);
    std::cout << vertex_descriptor(source) << std::endl;
    hm.add_source(source);
    hm.estimate_geodesic_distances(vertex_distance);

    unsigned long int vertex_id = 0;
    BOOST_FOREACH(vertex_descriptor vd , vertices(tm)){
	double v_distance = get(vertex_distance, vd);
	if(i == 0){
	  distances[vertex_id] = {0.0, v_distance};
	} else {
	  double current_vdist = distances[vertex_id][1];
	  if(v_distance < current_vdist){
	    distances[vertex_id] = {double(i), v_distance};
	  }
	}
	vertex_id++;
    }

    hm.remove_source(source);
  }
  return distances;
}


int main(int argc, char* argv[])
{
  Triangle_mesh tm;
  const char* filename = (argc > 1) ? argv[1] : "./data/heart_1.off";
  std::ifstream input(filename);
  if (!input || !(input >> tm) || tm.is_empty()) {
    std::cerr << "Not a valid off file." << std::endl;
    return 1;
  }
  
  //property map for the distance values to the source set
  Vertex_distance_map vertex_distance = tm.add_property_map<vertex_descriptor, double>("v:distance", 0).first;

  Heat_method hm(tm);
  //std::vector<int> randomSeeds;

  int upper = vertices(tm).size();
  
  std::vector<int> seedIds;
  int numClusters = 20;

  for(int i=0; i < numClusters; i++){
    //get random vertices to use as seeds
    seedIds.push_back(rand() % (upper + 1));
  }

  std::vector<std::array<double, 2>> distances = computeVoronoi(seedIds, tm, vertex_distance, hm);

  for(int iteration = 0; iteration < 10; iteration++){
    std::vector<std::vector<int>> clusters;
    for(int i=0; i < numClusters; i++){
	std::vector<int> cluster;
	clusters.push_back(cluster);
    }

    for(int i=0; i < distances.size(); i++){
	clusters[distances[i][0]].push_back(i);
    }

    for(int i=0; i < numClusters; i++){
	std::vector<int> cluster = clusters[i];
	for(int j=0; j < cluster.size(); j++){
	  int vertex_id = cluster[j];
	  //std::cout << "cluster id: " << i << " vertex id: " << vertex_id << std::endl;
	  vertex_descriptor(source) = *(vertices(tm).begin() + vertex_id);
	  hm.add_source(source);
	}

	hm.estimate_geodesic_distances(vertex_distance);

	for(int j=0; j < cluster.size(); j++){
	  int vertex_id = cluster[j];
	  vertex_descriptor(source) = *(vertices(tm).begin() + vertex_id);
	  double v_distance = get(vertex_distance, source);
	  std::cout << "vertex distance: " << v_distance << std::endl;
	  hm.remove_source(source);
	}
    }
  }


  std::ofstream outfile;
  outfile.open("vertex_colors.txt");

  for(unsigned long int i=0; i < distances.size(); i++){
    std::array<double, 2> voronoi_assignment = distances[i];
    std::cout << "vertex " << i << " is at " << voronoi_assignment[1] << " and has seed id " << voronoi_assignment[0] << std::endl;
    outfile << voronoi_assignment[0] << ",";
  }
  outfile.close();
  

  std::cout << "done" << std::endl;
  return 0;
}
