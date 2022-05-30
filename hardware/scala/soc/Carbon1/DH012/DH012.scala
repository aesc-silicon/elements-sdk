package elements.soc.carbon1

import spinal.core._
import spinal.core.sim._
import spinal.lib._

import spinal.lib.bus.amba3.apb._
import spinal.lib.bus.amba4.axi._

import nafarr.system.reset._
import nafarr.system.reset.ResetControllerCtrl._
import nafarr.system.clock._
import nafarr.system.clock.ClockControllerCtrl._
import nafarr.blackboxes.ihp.sg13s._

import zibal.misc._
import zibal.platform.Carbon
import zibal.board.{KitParameter, BoardParameter}

import elements.sdk.ElementsApp
import elements.board.DH012
import elements.soc.Carbon1

import zibal.sim.MT25Q

case class DH012Board() extends Component {
  val io = new Bundle {
    val clock = inout(Analog(Bool))
    val reset = inout(Analog(Bool))
    val jtag = new Bundle {
      val tdo = inout(Analog(Bool))
    }
    val uartStd = new Bundle {
      val txd = inout(Analog(Bool))
      val rts = inout(Analog(Bool))
    }
    val spiXip = new Bundle {
      val ss = inout(Analog(Bool))
      val sclk = inout(Analog(Bool))
      val mosi = inout(Analog(Bool))
      val miso = inout(Analog(Bool))
    }
    val gpioStatus = Vec(inout(Analog(Bool())), 4)
    val gpioA = Vec(inout(Analog(Bool())), 8)
  }

  val top = DH012Top()
  val analogFalse = Analog(Bool)
  analogFalse := False
  val analogTrue = Analog(Bool)
  analogTrue := True

  val spiNor = MT25Q()
  spiNor.io.clock := io.clock
  spiNor.io.dataClock := top.io.spiXip.sclk.PAD
  spiNor.io.reset := io.reset
  spiNor.io.chipSelect := top.io.spiXip.ss.PAD
  spiNor.io.dataIn := top.io.spiXip.mosi.PAD
  val analogDataOut = Analog(Bool)
  analogDataOut := spiNor.io.dataOut
  top.io.spiXip.miso.PAD := analogDataOut

  top.io.clock.PAD := io.clock
  top.io.reset.PAD := io.reset

  top.io.jtag.tms.PAD := analogFalse
  top.io.jtag.tdi.PAD := analogFalse
  io.jtag.tdo := top.io.jtag.tdo.PAD
  top.io.jtag.tck.PAD := analogFalse
  io.spiXip.ss := top.io.spiXip.ss.PAD
  io.spiXip.sclk := top.io.spiXip.sclk.PAD
  io.spiXip.mosi := top.io.spiXip.mosi.PAD
  top.io.spiXip.miso.PAD := io.spiXip.miso
  top.io.uartStd.rxd.PAD := analogFalse
  io.uartStd.txd := top.io.uartStd.txd.PAD
  top.io.uartStd.cts.PAD := analogFalse
  io.uartStd.rts := top.io.uartStd.rts.PAD

  top.io.i2cA.scl.PAD := analogFalse
  top.io.i2cA.sda.PAD := analogFalse

  for (index <- 0 until 4) {
    io.gpioStatus(index) <> top.io.gpioStatus(index).PAD
  }

  for (index <- 0 until 8) {
    io.gpioA(index) <> top.io.gpioA(index).PAD
  }

  val baudPeriod = top.soc.socParameter.uartStd.init.getBaudPeriod()

  def simHook() {}
}

case class DH012Top() extends Component {
  val resets = List[ResetParameter](ResetParameter("system", 64))
  val clocks = List[ClockParameter](ClockParameter("system", 50 MHz, "system"))

  val kitParameter = KitParameter(resets, clocks)
  val boardParameter = DH012.Parameter(kitParameter)
  val socParameter = Carbon1.Parameter(boardParameter)
  val parameter = Carbon.Parameter(
    socParameter,
    512 Byte,
    4 MB,
    (resetCtrl: ResetControllerCtrl, reset: Bool, _) => { resetCtrl.buildDummy(reset) },
    (clockCtrl: ClockControllerCtrl, _, clock: Bool) => { clockCtrl.buildDummy(clock) },
    (onChipRamSize: BigInt) => {
      val ram = Axi4SharedOnChipRam(
        dataWidth = 32,
        byteCount = onChipRamSize,
        idWidth = 4
      )
      ram.io.axi
    }
  )

  val io = new Bundle {
    val clock = IhpCmosIo("top", 0)
    val reset = IhpCmosIo("top", 1)
    val jtag = new Bundle {
      val tms = IhpCmosIo("right", 0)
      val tdi = IhpCmosIo("right", 1)
      val tdo = IhpCmosIo("right", 2)
      val tck = IhpCmosIo("right", 3)
    }
    val uartStd = new Bundle {
      val txd = IhpCmosIo("bottom", 7)
      val rxd = IhpCmosIo("bottom", 8)
      val rts = IhpCmosIo("bottom", 9)
      val cts = IhpCmosIo("bottom", 10)
    }
    val spiXip = new Bundle {
      val ss = IhpCmosIo("left", 0)
      val sclk = IhpCmosIo("left", 1)
      val mosi = IhpCmosIo("left", 2)
      val miso = IhpCmosIo("left", 3)
    }
    val i2cA = new Bundle {
      val scl = IhpCmosIo("left", 8)
      val sda = IhpCmosIo("left", 9)
    }
    val gpioStatus =
      Vec(IhpCmosIo("top", 7), IhpCmosIo("top", 8), IhpCmosIo("top", 9), IhpCmosIo("top", 10))
    val gpioA = Vec(
      IhpCmosIo("right", 8),
      IhpCmosIo("right", 9),
      IhpCmosIo("right", 10),
      IhpCmosIo("bottom", 0),
      IhpCmosIo("bottom", 1),
      IhpCmosIo("bottom", 2),
      IhpCmosIo("left", 10),
      IhpCmosIo("top", 2)
    )
  }

  val soc = Carbon1(parameter)

  io.clock <> ixc013_i16x(soc.io_plat.clock)
  io.reset <> ixc013_i16x(soc.io_plat.reset)

  io.jtag.tms <> ixc013_b16m().asInput(soc.io_plat.jtag.tms)
  io.jtag.tdi <> ixc013_b16m().asInput(soc.io_plat.jtag.tdi)
  io.jtag.tdo <> ixc013_b16m().asOutput(soc.io_plat.jtag.tdo)
  io.jtag.tck <> ixc013_b16m().asInput(soc.io_plat.jtag.tck)

  io.spiXip.ss <> ixc013_b16m().asOutput(soc.io_plat.spiXip.ss(0))
  io.spiXip.sclk <> ixc013_b16m().asOutput(soc.io_plat.spiXip.sclk)
  io.spiXip.mosi <> ixc013_b16m().asOutput(soc.io_plat.spiXip.mosi)
  io.spiXip.miso <> ixc013_b16m().asInput(soc.io_plat.spiXip.miso)

  io.uartStd.txd <> ixc013_b16m().asOutput(soc.io_per.uartStd.txd)
  io.uartStd.rxd <> ixc013_b16m().asInput(soc.io_per.uartStd.rxd)
  io.uartStd.rts <> ixc013_b16m().asOutput(soc.io_per.uartStd.rts)
  io.uartStd.cts <> ixc013_b16m().asInput(soc.io_per.uartStd.cts)

  io.i2cA.scl <> ixc013_b16mpup().withOpenDrain(soc.io_per.i2cA.scl)
  io.i2cA.sda <> ixc013_b16mpup().withOpenDrain(soc.io_per.i2cA.sda)

  for (index <- 0 until 4) {
    io.gpioStatus(index) <> ixc013_b16m(soc.io_per.gpioStatus.pins(index))
  }

  for (index <- 0 until 8) {
    io.gpioA(index) <> ixc013_b16m(soc.io_per.gpioA.pins(index))
  }
}

object DH012Prepare extends ElementsApp {
  elementsConfig.genASICSpinalConfig.generateVerilog {
    val top = DH012Top()

    top.soc.prepareBaremetal("baremetal0", elementsConfig)

    val embench = EmbenchIotTools(elementsConfig)
    embench.generate(top.soc.clockCtrl.getClockDomainByName("system").frequency.getValue)

    val io = CadenceTools.Io(elementsConfig)
    io.addPad("top", 3, "gndpad")
    io.addPad("top", 4, "gndcore")
    io.addPad("top", 5, "vddcore")
    io.addPad("top", 6, "vddpad")
    io.addPad("right", 4, "gndpad")
    io.addPad("right", 5, "gndcore")
    io.addPad("right", 6, "vddcore")
    io.addPad("right", 7, "vddpad")
    io.addPad("bottom", 3, "gndpad")
    io.addPad("bottom", 4, "gndcore")
    io.addPad("bottom", 5, "vddcore")
    io.addPad("bottom", 6, "vddpad")
    io.addPad("left", 4, "gndpad")
    io.addPad("left", 5, "gndcore")
    io.addPad("left", 6, "vddcore")
    io.addPad("left", 7, "vddpad")
    io.addCorner("topright", 90, "corner")
    io.addCorner("bottomright", 0, "corner")
    io.addCorner("bottomleft", 270, "corner")
    io.addCorner("topleft", 180, "corner")
    io.generate(top.io, elementsConfig.zibalBuildPath)

    val sdc = CadenceTools.Sdc(elementsConfig)
    sdc.addClock(top.io.clock.PAD, top.boardParameter.getOscillatorFrequency)
    sdc.addClock(top.io.jtag.tck.PAD, top.boardParameter.getJtagFrequency)
    sdc.generate(elementsConfig.zibalBuildPath)

    top
  }
}

object DH012Generate extends ElementsApp {
  elementsConfig.genASICSpinalConfig.generateVerilog {
    val top = DH012Top()
    top
  }
}

object DH012Simulate extends ElementsApp {
  val compiled = elementsConfig.genASICSimConfig.compile {
    val board = DH012Board()
    BinTools.initRam(
      board.spiNor.deviceOut.data,
      elementsConfig.swStorageBaremetalImage("baremetal0")
    )
    board
  }
  simType match {
    case "simulate" =>
      compiled.doSimUntilVoid("simulate") { dut =>
        dut.simHook()
        val testCases = TestCases()
        testCases.addClock(dut.io.clock, DH012.oscillatorFrequency, 150 ms)
        testCases.addReset(dut.io.reset, 1 us)
        testCases.dump(dut.io.uartStd.txd, dut.baudPeriod)
      }
    case _ =>
      println(s"Unknown simulation ${simType}")
  }
}
