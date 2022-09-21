val spinalVersion = "1.7.3"

lazy val root = (project in file(".")).
  settings(
    name := "Elements",
    inThisBuild(List(
      organization := "com.github.spinalhdl",
      scalaVersion := "2.11.12",
      version      := spinalVersion
    )),
    libraryDependencies ++= Seq(
      "com.github.spinalhdl" % "spinalhdl-core_2.11" % spinalVersion,
      "com.github.spinalhdl" % "spinalhdl-lib_2.11" % spinalVersion,
      compilerPlugin("com.github.spinalhdl" % "spinalhdl-idsl-plugin_2.11" % spinalVersion),
      "org.scalatest" %% "scalatest" % "3.2.5",
      "org.yaml" % "snakeyaml" % "1.8",
    ),
    scalaSource in Compile := baseDirectory.value / "hardware" / "scala",
    scalaSource in Test    := baseDirectory.value / "test" / "scala"
  ).dependsOn(vexRiscv, zibal, nafarr)

lazy val vexRiscv = RootProject(file("internal/vexriscv/"))
lazy val zibal = RootProject(file("internal/zibal/"))
lazy val nafarr = RootProject(file("internal/nafarr/"))

connectInput in run := true
fork := true
