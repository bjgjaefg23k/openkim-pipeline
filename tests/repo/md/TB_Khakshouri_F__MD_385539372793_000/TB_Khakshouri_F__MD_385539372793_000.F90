
#include "KIM_API_status.h"
#define THIS_FILE_NAME "HELP"


    module TB_Khakshouri
!---^^^^^^^^^^^^^^^^^^^^
!*      An implementation of the
!*      temperature dependent interatomic potential due to Khakshouri, Alfè and Duffy
!*
!*          Development of an electron-temperature-dependent interatomic potential
!*          for molecular dynamics simulation of tungsten under electronic excitation
!*
!*          S. Khakshouri, D. Alfè, and D. M. Duffy
!*          PHYSICAL REVIEW B 78, 224304 2008
!*
!*          Irradiation of a metal by lasers or swift heavy ions causes the electrons to become excited. In the vicinity of
!*          the excitation, an electronic temperature is established within a thermalization time of 10–100 fs, as a result of
!*          electron-electron collisions. For short times, corresponding to less than 1 ps after excitation, the resulting
!*          electronic temperature may be orders of magnitude higher than the lattice temperature. During this short time,
!*          atoms in the metal experience modified interatomic forces as a result of the excited electrons. These forces can
!*          lead to ultrafast nonthermal phenomena such as melting, ablation, laser-induced phase transitions, and modified
!*          vibrational properties. We develop an electron-temperature-dependent empirical interatomic potential for tungsten
!*          that can be used to model such phenomena using classical molecular dynamics simulations. Finitetemperature
!*          density functional theory calculations at high electronic temperatures are used to parametrize the
!*          model potential.
!*
!*
!*          In this module temperature is expressed in eV ( ie "Temperature" Te really means kB Te )
!*
!*          In this implementation an additional switch is added to prevent the free energy going to -infinity
!*          as the atoms are separated. Set use_DRM_temperatureswitch=.false. to return to the original paper version.
!*
!*          Implementation
!*          Author      :   Daniel Mason
!*          Version     :   1.0
!*          Revision    :   April 2012
!*

        use KIM_API
        use Lib_dilog
        use Lib_QuinticSpline
        use TB_SmoothSwitches
        use TB_FinnisSinclair
        implicit none
        private


    !---    KIM API

        public      ::      Compute_Energy_Forces_KH
        public      ::      Destroy_KH

    !---


        public      ::      Khakshouri_ctor
        public      ::      report
        public      ::      delete

        public      ::      getNe,getNa
        public      ::      getFinnisSinclair
        public      ::      getCutoff
        public      ::      use_DRM_temperatureswitch
        public      ::      setUse_DRM_temperatureswitch
        public      ::      freeEnergy

    !---


!-------    static members

        type,public     ::      Khakshouri
            private
        !---    these parameters are needed for temperature dependence
            real(kind=8)            ::      Ne          !   number of d-band electrons          should be 0,1,2..10, but is tuneable
            real(kind=8)            ::      Na          !   number of d-band states             should be 5, but is tuneable

        !---    this is the original Finnis & Sinclair second moment model
            type(FinnisSinclair)    ::      fs

        !---    this is a derived parameter
            real(kind=8)            ::      Khakshouri_12onNac    !   see eq 28

        !---    this is a switch to stop the electronic temperature being too high
        !       when Wi->0 ( ie the local density of states becomes isolated-atom-like )
            logical                 ::      use_DRM_temperatureswitch
            type(SmoothSwitch)      ::      T_sw


        end type


        real(kind=8),public,parameter   ::      KHAKSHOURI_BOLTZMANN = 0.861734255962E-04   ! eV/K

    !---

        interface   Khakshouri_ctor
            module procedure        Khakshouri_null
            module procedure        Khakshouri_ctor0
        end interface

        interface   report
            module procedure        report0
        end interface

        interface   delete
            module procedure        delete0
        end interface



        interface ionicPotentialEnergy
            module procedure    Khakshouri_atomic1
        end interface

        interface getCutoff
           module procedure getCutoffKhakshouri
        end interface




        interface   addForce
            module procedure    addForceKhakshouri1
            module procedure    addForceKhakshouri2
        end interface


        interface bandEnergy
           module procedure     bandEnergy0
        end interface

        interface dbandEnergy
           module procedure     dbandEnergy0
        end interface




    !---

        real(kind=8),private,parameter          ::      TB_KHAKSHOURI_SMALLTE  = 1.0d-8     !    eV - point at which zero temperature assumed
        real(kind=8),private,parameter          ::      TB_KHAKSHOURI_SMALLWI  = 1.0d-6      !    eV - point at which delta-fn d-band assumed
        real(kind=8),private,parameter          ::      TB_KHAKSHOURI_SMALLRHO = 1.0d-12    !    point at which density assumed zero

    contains
!---^^^^^^^^

        function Khakshouri_null( ) result(this)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !       null constructor for Khakshouri potential - returns the
    !       Tungsten model from the original paper.
            type(Khakshouri)    ::      this
            type(FinnisSinclair)    ::  fs
            fs = FinnisSinclair_ctor()
            this = Khakshouri_ctor0( 6.5826d0,7.3592d0,fs )
            return
        end function Khakshouri_null


        function Khakshouri_ctor0( Ne,Na,fs ) result(this)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !       default constructor for Khakshouri potential
            real(kind=8),intent(in)     ::      Ne,Na
            type(FinnisSinclair),intent(in) ::  fs
            type(Khakshouri)    ::      this

            this%Ne = Ne
            this%Na = Na
            this%fs = fs
        !---    sanity check
            if (Ne > 2*Na) then
                write(unit=0,fmt='(a,2g16.8)') "(Ne,Na) = ",Ne,Na
                stop "TB_Khakshouri::Khakshouri_ctor0 error - Ne > 2*Na"
            end if
            this%Khakshouri_12onNac = 4.0*getA(this%fs)*this%Na                &                   !   using a dummy for ease of
                                    / (this%Ne*(this%Ne - 2*this%Na))                       !   construction
            this%Khakshouri_12onNac = this%Khakshouri_12onNac * this%Khakshouri_12onNac     !   see eqn 28 in Khakshouri paper.
        !---    initialise dilogarithm function
            call initialise_qdilog()


            this%T_sw = SmoothSwitch_ctor( 0.0d0,2.0d0 )
            this%use_DRM_temperatureswitch = .true.
            return
        end function Khakshouri_ctor0

        subroutine report0( this,u )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            type(Khakshouri),intent(in)         ::      this
            integer,intent(in),optional         ::      u
            integer         ::      uu
            uu = 6
            if (present(u)) uu = u
            write (unit=uu,fmt='(a)') "Khakshouri"
            write (unit=uu,fmt='(a,2f16.8)') "    (Ne,Na)      = ",this%Ne,this%Na
            call report(this%fs,uu)
            return
        end subroutine report0

        subroutine delete0( this )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^
            type(Khakshouri),intent(inout)      ::      this
            call delete(this%fs)
            call delete(this%T_sw)
            return
        end subroutine delete0

!-------

        pure function bandwidth( this,rho ) result( W )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      the bandwidth of the ldos is proportional to the square-root
    !*      of the electron density ( eqn 28 )
            type(Khakshouri),intent(in)     ::      this
            real(kind=8),intent(in)                 ::      rho
            real(kind=8)                            ::      W
            W = sqrt( this%Khakshouri_12onNac * rho )
            return
        end function bandwidth

        pure subroutine dbandwidth( this,rho , W,dWdrho )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      compute bandwidth and
    !*      the derivative of the bandwidth with respect to
    !*      density
            type(Khakshouri),intent(in)             ::      this
            real(kind=8),intent(in)                 ::      rho
            real(kind=8),intent(out)                ::      W,dWdrho
            W = sqrt( this%Khakshouri_12onNac * rho )
            if (rho<TB_KHAKSHOURI_SMALLRHO) then
                dWdrho = 0.0
            else
                dWdrho = 0.5*sqrt( this%Khakshouri_12onNac / rho )
            end if
            return
        end subroutine dbandwidth

        pure function bandEnergy0( this,rho,Te ) result( E )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      compute the band energy from the electron density and the
    !*      electronic temperature ( eqn 19 )
            type(Khakshouri),intent(in)     ::      this
            real(kind=8),intent(in)                 ::      rho
            real(kind=8),intent(in)                 ::      Te
            real(kind=8)                            ::      E
            real(kind=8)            ::      Wi,ai
            real(kind=8)            ::      mu
            Wi = bandwidth( this,rho )
            if (Te<TB_KHAKSHOURI_SMALLTE) then              !   zero temperature limit
                E = this%Ne*Wi*0.25*(this%Ne/this%Na-2)     !   note: eqn 13 is in error.
            else if (Wi>100.0*Te) then                       !   large bandwidth limit:
                E = this%Ne*Wi*0.25*(this%Ne/this%Na-2)     !   note: eqn 13 is in error.
            else if (Wi<TB_KHAKSHOURI_SMALLWI) then         !   zero bandwidth limit
                E = -this%Ne*Wi*0.5 + this%Ne*Te
            else
                mu = log( exp( this%Ne*Wi / (2*this%Na*Te) ) - 1.0 )
                E = - this%Ne*Wi*0.5 - 2*this%Na*Te*Te*dilog( mu )/Wi     !   note: this expression is identical to eqn 19 if eqn 22 is substituted.
            end if
            return
        end function bandEnergy0

        subroutine dbandEnergy0( this,rho,Te , E,dEdrho,dEdTe )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      compute the band energy from the electron density and the
    !*      electronic temperature ( eqn 19 )
    !*      and its derivatives with respect to density and temperature
            type(Khakshouri),intent(in)     ::      this
            real(kind=8),intent(in)                 ::      rho
            real(kind=8),intent(in)                 ::      Te
            real(kind=8),intent(out)                ::      E
            real(kind=8),intent(out)                ::      dEdrho,dEdTe
            real(kind=8)            ::      iTe,iWi
            real(kind=8)            ::      Wi,ai
            real(kind=8)            ::      dWidrho,daidWi,daidrho,daidTe
            real(kind=8)            ::      mu,emu,dmudrho,dmudTe
            real(kind=8)            ::      dilogmu,ddilogmu


            call dbandwidth( this,rho, Wi,dWidrho)                     !   y
            if (Te<TB_KHAKSHOURI_SMALLTE) then              !   zero temperature limit
                E       = this%Ne*Wi*0.25*(this%Ne/this%Na-2)     !   note: eqn 13 is in error.
                dEdrho  = this%Ne*dWidrho*0.25*(this%Ne/this%Na-2)
                dEdTe   = 0.0
            else if (Wi>100.0*Te) then                       !   large bandwidth limit:
                E       = this%Ne*Wi*0.25*(this%Ne/this%Na-2)     !   note: eqn 13 is in error.
                dEdrho  = this%Ne*dWidrho*0.25*(this%Ne/this%Na-2)
                dEdTe   = 0.0
            else if (Wi<TB_KHAKSHOURI_SMALLWI) then         !   zero bandwidth limit
                E       = -this%Ne*Wi*0.5 + this%Ne*Te
                dEdrho  = -this%Ne*0.5*dWidrho
                dEdTe   = this%Ne
            else
                iTe     = 1.0/Te
                iWi     = 1.0/Wi
                emu     = exp( (this%Ne/(2*this%Na)) * Wi * iTe )
                mu      = log( emu - 1.0 )                                                      !   y
                dmudrho =   (emu/(emu - 1.0)) * (this%Ne/(2*this%Na)) * dWidrho * iTe           !   y
                dmudTe  = - (emu/(emu - 1.0)) * (this%Ne/(2*this%Na)) * Wi * iTe*iTe            !   y
                call ddilog( mu,dilogmu,ddilogmu )
                E       = -this%Ne*Wi*0.5 - 2*this%Na*Te*Te*dilogmu*iWi    !   note: this expression is identical to eqn 19 if eqn 22 is substituted.
                dEdrho  = -this%Ne*0.5*dWidrho + 2*this%Na*Te*Te*dilogmu*dWidrho*iWi*iWi            &
                        - 2*this%Na*Te*Te*ddilogmu*dmudrho*iWi
                dEdTe   = -4*this%Na*Te*dilogmu*iWi                                                 &
                        - 2*this%Na*Te*Te*ddilogmu*dmudTe*iWi

            end if
            return
        end subroutine dbandEnergy0


    !---

        pure function entropy( this, rho,Te ) result( S )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      note: actually returns S/kB. Recall Te is really kB T, so Te S has units eV.
            type(Khakshouri),intent(in)     ::      this
            real(kind=8),intent(in)                 ::      rho,Te
            real(kind=8)                            ::      S
            real(kind=8)            ::      mu,emu
            real(kind=8)            ::      Wi
            Wi = bandwidth( this,rho )
            if (Te<TB_KHAKSHOURI_SMALLTE) then              !   zero temperature limit
                S     = 0.0
            else
                if (Wi < TB_KHAKSHOURI_SMALLWI) then
                    S     = 0.0
                else
                    mu = this%Ne*Wi/(2*this%Na*Te)
                    if (mu < 30.0) then
                        emu = exp(mu)
                        S = log( 1 - 1.0/emu )*(log(1-1.0/emu) + mu)
                        S = - (this%Ne/mu) * ( S + 2*dilog( -log(emu-1) ) )
                    else
                        emu = exp(-mu)
                        S = 2* (this%Ne/mu) * emu
                    end if
                end if
            end if
            return
        end function entropy


        subroutine dentropy( this, rho,Te , S,dSdrho,dSdTe )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      note: actually returns S/kB. Recall Te is really kB T, so Te S has units eV.
            type(Khakshouri),intent(in)     ::      this
            real(kind=8),intent(in)                 ::      rho,Te
            real(kind=8),intent(out)                ::      S,dSdrho,dSdTe
            real(kind=8)            ::      mu,emu,xx,yy,dd,dmudWi,dmudTe,iTe,imu,dWidrho,Wi,zz
            real(kind=8)            ::      dilogmu,ddilogmu

            if (Te<TB_KHAKSHOURI_SMALLTE) then              !   zero temperature limit
                S     = 0.0
                dSdrho = 0.0
                dSdTe = 0.0
            else
                call dbandwidth( this,rho, Wi,dWidrho)                     !   y
                if (Wi < TB_KHAKSHOURI_SMALLWI) then
                    S     = 0.0
                    dSdrho = 0.0
                    dSdTe = 0.0
                else
                    iTe = 1.0/Te
                    mu  = ( this%Ne/(2*this%Na) ) * Wi * iTe
                    if (mu < 30.0) then
                        emu    = exp(mu)                !   demu/dmu = emu
                        zz     = emu/(emu-1)            !   dz/dmu = emu/(emu-1) - emu*emu/(emu-1)*2 = z - z*z
                        xx     = -log( zz )             !   dx/dmu = -1/z dz/dmu = (z - 1) =  emu/(emu-1) - 1 = 1/(emu-1)
                        yy     = xx*(xx + mu)           !   dy/dmu = (2x+mu) dx/dmu + x = (2x+mu)(z-1) + x
                        call ddilog( -log(emu-1) , dilogmu,ddilogmu )
                        imu    = 1.0/mu
                        dmudWi = mu/Wi
                        dmudTe = - mu * iTe

                        S      = - (this%Ne*imu) * ( yy + 2*dilogmu )

                        dd     = (this%Ne*imu*imu)*( yy + 2*dilogmu )               &
                               - (this%Ne*imu) * ( (2*xx + mu)*(zz-1) + xx )            &
                               + (this%Ne*imu) * 2 * ddilogmu*zz

                        dSdrho = dd*dmudWi*dWidrho
                        dSdTe  = dd*dmudTe

                    else
                        emu    = exp(-mu)
                        imu    = 1.0/mu
                        S      = 2* (this%Ne*imu) * emu
                        dmudWi = mu/Wi
                        dmudTe = - mu * iTe

                        dd     = -2*this%Ne*imu*(1 + imu) * emu

                        dSdrho = dd*dmudWi*dWidrho
                        dSdTe  = dd*dmudTe

                    end if
                end if
            end if

            return
        end subroutine dentropy

    !---

        function freeEnergy( this, rho,Te ) result( F )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns F = E - TS
            type(Khakshouri),intent(in)     ::      this
            real(kind=8),intent(in)                 ::      rho,Te
            real(kind=8)                            ::      F

            real(kind=8)        ::      T

            T = modifiedTemperature( this,rho,Te )
            F = bandEnergy( this,rho,T ) - T*entropy( this,rho,T )

            return
        end function freeEnergy


        subroutine dfreeEnergy( this, rho,Te , F,dFdrho,dFdTe )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns F = E - TS
            type(Khakshouri),intent(in)     ::      this
            real(kind=8),intent(in)                 ::      rho,Te
            real(kind=8),intent(out)                ::      F,dFdrho,dFdTe

            real(kind=8)        ::      E,dEdrho,dEdT,dEdTe
            real(kind=8)        ::      S,dSdrho,dSdT,dSdTe
            real(kind=8)        ::      T,dTdrho,dTdTe

            call dModifiedTemperature( this,rho,Te , T,dTdrho,dTdTe )

            call dbandEnergy( this, rho,T , E,dEdrho,dEdT )
            dEdrho = dEdrho + dEdT*dTdrho
            dEdTe = dEdT*dTdTe
            call dentropy( this, rho,T , S,dSdrho,dSdT )
            dSdrho = dSdrho + dSdT*dTdrho
            dSdTe = dSdT*dTdTe

            F      = E - T*S
            dFdrho = dEdrho - S*dTdrho - T*dSdrho
            dFdTe  = dEdTe - S*dTdTe - T*dSdTe

            return
        end subroutine dfreeEnergy




!-------

        pure function getNa(this) result(Na)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      simple accessor for number of electron states
            type(Khakshouri),intent(in)     ::      this
            real(kind=8)                            ::      Na
            Na = this%Na
            return
        end function getNa

        pure function getNe(this) result(Ne)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      simple accessor for number of electrons
            type(Khakshouri),intent(in)     ::      this
            real(kind=8)                            ::      Ne
            Ne = this%Ne
            return
        end function getNe

        function getFinnisSinclair(this) result(fs)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            type(Khakshouri),intent(in)     ::      this
            type(FinnisSinclair)            ::      fs
            fs = this%fs
            return
        end function getFinnisSinclair

        pure function getCutoffKhakshouri(this) result(c)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        !*  Returns the cutoff range
            type(Khakshouri), intent(in):: this
            real(kind=8) :: c
            c = getCutoff(this%fs)
            return
        end function getCutoffKhakshouri

        pure function use_DRM_temperatureswitch(this) result(is)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        !*  returns true if the temperature switch to prevent entropy overflow at
        !*  small bandwidth is applied
            type(Khakshouri), intent(in)    :: this
            logical                         :: is
            is = this%use_DRM_temperatureswitch
            return
        end function use_DRM_temperatureswitch


        pure subroutine setUse_DRM_temperatureswitch(this,is)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        !*  decide if the temperature switch to prevent entropy overflow at
        !*  small bandwidth is applied
            type(Khakshouri), intent(inout) :: this
            logical,intent(in)              :: is
            this%use_DRM_temperatureswitch = is
            return
        end subroutine setUse_DRM_temperatureswitch




!------------------------------------------------------------------------------


        pure function modifiedTemperature( this, rho,Te ) result( T )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        !*  I add the following to fix the instability at small Wi:
        !*  The entropy at small Wi goes as S ~ -k Ne ln( Ne Wi / 2 Na k T )
        !*  ... which blows as Wi -> 0!
        !*  So fix this by insisting kT <= Ne Wi / (2 Na )
        !*  This is not an excessively onerous requirement as Wi ~ 5 eV
        !*  and kT must be ~ 0.025 eV at 300K.

            type(Khakshouri), intent(in)    ::  this
            real(kind=8),intent(in)         ::  rho
            real(kind=8),intent(in)         ::  Te
            real(kind=8)                    ::  T
            real(kind=8)        ::      Wi
            real(kind=8)        ::      xx,pp
            if (.not. this%use_DRM_temperatureSwitch) then
                T = Te
            else
                if (Te < TB_KHAKSHOURI_SMALLTE) then
                    T = Te
                else
                    Wi = bandwidth( this,rho )
                    xx = Wi*this%Ne/(this%Na*Te)
                    pp = switch( this%T_sw,xx, 1.0d0 )
                    T = pp * Wi*this%Ne/(2*this%Na) + (1.0d0-pp)*Te
                end if
            end if
            return
        end function modifiedTemperature

        pure subroutine dModifiedTemperature( this, rho,Te , T,dTdrho,dTdTe )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        !*  insist kT <= Ne Wi / (2 Na )

            type(Khakshouri), intent(in)    ::  this
            real(kind=8),intent(in)         ::  rho
            real(kind=8),intent(in)         ::  Te
            real(kind=8),intent(out)        ::  T
            real(kind=8),intent(out)        ::  dTdrho
            real(kind=8),intent(out)        ::  dTdTe
            real(kind=8)        ::      Wi,dWidrho,dTdWi
            real(kind=8)        ::      xx,pp,dpp,dpdrho,dpdTe

            if (.not. this%use_DRM_temperatureSwitch) then
                T = Te
                dTdrho = 0.0
                dTdTe = 1.0
            else
                if (Te < TB_KHAKSHOURI_SMALLTE) then
                    T = Te
                    dTdrho = 0.0
                    dTdTe = 1.0
                else
                    call dBandwidth( this,rho,Wi,dWidrho )
                    if ( Wi > getCutoff(this%T_sw)*Te*this%Na/this%Ne ) then
                        T = Te
                        dTdrho = 0.0
                        dTdTe = 1.0
                    else
                        xx = Wi*this%Ne/(this%Na*Te)
                        pp = switch( this%T_sw,xx, 1.0d0 )
                        dpp = switchDerivative( this%T_sw,xx, 1.0d0,0.0d0 )
                        dpdrho = dpp*this%Ne/(this%Na*Te)*dWidrho
                        dpdTe = -dpp*Wi*this%Ne/(this%Na*Te*Te)

                        T = pp * Wi*this%Ne/(2*this%Na) + (1.0d0-pp)*Te
                        dTdrho = dpdrho* ( Wi*this%Ne/(2*this%Na) - Te ) + pp*this%Ne/(2*this%Na)*dWidrho
                        dTdTe  = dpdTe* ( Wi*this%Ne/(2*this%Na) - Te ) + (1.0d0-pp)
                    end if
                end if
            end if
            return
        end subroutine dModifiedTemperature








!-------        potential energy of ions




        function Khakshouri_atomic1(this, i ,Te ,pkim) result(pe)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        !*  Constructs the potential energy of atom i
            type(Khakshouri), intent(inout)                 ::  this
            integer,intent(in)                              ::  i
            real(kind=8),intent(in)                         ::  Te
            !-- Transferred variables
            integer(kind=kim_intptr), intent(in) :: pkim

            real(kind=8)                                            ::  pe

            integer                 ::  ii,kk,nn
            real(kind=8)            ::  att,rep,modrij,rho


            integer                 ::  nei1atom(1);    pointer(pnei1atom,nei1atom)
            real(kind=8)            ::  rij_(3,1);      pointer(pRij,Rij_)
            real(kind=8),dimension(:,:),pointer   ::  rij
            integer                 ::  ier,idum,atom_ret
            integer,parameter       ::  LOCATOR_MODE = 1


        !---   CALL TO NEIGHBOUR LIST FOR ATOM i
            ier = kim_api_get_neigh_f(pkim,LOCATOR_MODE,i,atom_ret,nn,pnei1atom,pRij)
            if (ier.lt.KIM_STATUS_OK) then
                idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                              "kim_api_get_neigh_f", ier)
                return
            end if
            call KIM_to_F90_real_array_2d(Rij_,rij,3,nn)
        !---

            rho = 0.0
            rep = 0.0
            do kk = 1,nn
                modrij = sqrt( rij(1,kk)*rij(1,kk) + rij(2,kk)*rij(2,kk) + rij(3,kk)*rij(3,kk) )
                rep  = rep + repulsivePairPotential( this%fs,modrij )
                rho  = rho + cohesivePairPotential( this%fs,modrij )
            end do
            att = FreeEnergy( this, rho , Te )
            pe = pe + 0.5*rep + att
            return
        end function Khakshouri_atomic1

!-------    ionic contribution to force


        subroutine addForceKhakshouri1(this, i,Te, force, pkim )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        !*  Calculates the force on a single atom "i"
            type(Khakshouri), intent(in)        ::  this
            integer,intent(in)                  ::  i
            real(kind=8),intent(in)             ::  Te
            real(kind=8),dimension(:,:),intent(inout)     ::  force

            !-- Transferred variables
            integer(kind=kim_intptr), intent(in) :: pkim

            integer                     ::  nni
            integer                     ::  nei1atom(1);    pointer(pnei1atom,nei1atom)
            real(kind=8)                ::  rij_(3,1);      pointer(pRij,Rij_)
            integer                     ::  ier,idum,atom_ret
            integer,parameter           ::  LOCATOR_MODE = 1
            real(kind=8),dimension(:,:),pointer     ::  rij
            integer,dimension(:),pointer            ::  neighbourj


        !---   CALL TO NEIGHBOUR LIST FOR ATOM i
            ier = kim_api_get_neigh_f(pkim,LOCATOR_MODE,i,atom_ret,nni,pnei1atom,pRij)
            if (ier.lt.KIM_STATUS_OK) then
                idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                              "kim_api_get_neigh_f", ier)
                return
            end if
            call KIM_to_F90_real_array_2d(Rij_,rij,3,nni)
            call KIM_to_F90_int_array_1d(nei1atom,neighbourj,nni)
        !---

            call addForceKhakshouri2(this, Te,i,rij,neighbourj,nni, force )
            return
        end subroutine addForceKhakshouri1


        subroutine addForceKhakshouri2(this, Te,i,rij,neigh,nn, force )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        !*  Calculates the forces due a single atom i given its neighbour list and temperature Te
            type(Khakshouri), intent(in)                ::  this
            real(kind=8),intent(in)                     ::  Te
            integer,intent(in)                          ::  i,nn
            real(kind=8),dimension(:,:),intent(in)      ::  rij
            integer,dimension(:),intent(in)             ::  neigh
            real(kind=8),dimension(:,:),intent(inout)   ::  force

            integer                     ::  ii,jj,kk
            real(kind=8)                ::  modrij, fij, V,dVdr, phi,dphidr,rho, FF,dFdrho,dFdTe
            real(kind=8),dimension(3)   ::  fi

        !---
            rho = 0.0
        !---    sum contributions to electron density
            do kk = 1,nn
                modrij = sqrt( rij(1,kk)*rij(1,kk) + rij(2,kk)*rij(2,kk) + rij(3,kk)*rij(3,kk) )
                rho = rho + cohesivePairPotential( this%fs,modrij )
            end do

            call dFreeEnergy( this,rho,Te, FF,dFdrho,dFdTe )

            do kk = 1,nn

                modrij = sqrt( rij(1,kk)*rij(1,kk) + rij(2,kk)*rij(2,kk) + rij(3,kk)*rij(3,kk) )
            !---    repulsive contribution
                call drepulsivePairPotential( this%fs,modrij , V,dVdr )
            !---    attractive contribution
                call dcohesivePairPotential( this%fs,modrij , phi,dphidr )

                fi = (0.5*dVdr + dFdrho*dphidr)*rij(:,kk)/modrij
                force(:,i)  = force(:,i) + fi
                jj = neigh(kk)
                force(:,jj) = force(:,jj) - fi

            end do
            return
        end subroutine addForceKhakshouri2



!------------------------------------------------------------------------------


!-------


        integer function Destroy_KH(pkim)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            use KIM_API
            implicit none

            !-- Transferred variables
            integer(kind=kim_intptr), intent(in) :: pkim

            !-- Local variables
            real(kind=8),dimension(1)   ::      buffer; pointer(pbuffer,buffer)
            integer idum

            call delete(qdilog)

            pbuffer = kim_api_get_model_buffer_f(pkim,Destroy_KH)
            if (Destroy_KH < KIM_STATUS_OK) then
                idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                              "kim_api_get_model_buffer_f", Destroy_KH)
                return
            end if
            call free(pbuffer)

            Destroy_KH = KIM_STATUS_OK
            return
        end function Destroy_KH



!-------------------------------------------------------------------------------
!
! Compute energy and forces on atoms from the positions.
!
!-------------------------------------------------------------------------------
        integer function Compute_Energy_Forces_KH(pkim)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            implicit none

            !-- Transferred variables
            integer(kind=kim_intptr), intent(in)  :: pkim

            !-- Local variables
            integer         ::      ier
            integer         ::      ii
            real(kind=8)            ::      Ei

            !-- KIM variables
            integer numberOfParticles;      pointer(pnAtoms,numberOfParticles)
            real(kind=8)      ::  temp;           pointer(ptemp,temp)

            real(kind=8)      ::  energy;         pointer(penergy,energy)
            real(kind=8)      ::  coordum(3,1);   pointer(pcoor,coordum)
            real(kind=8)      ::  forcedum(3,1);  pointer(pforce,forcedum)
            real(kind=8)      ::  enepotdum(1);   pointer(penepot,enepotdum)
            real(kind=8), pointer :: coor(:,:),force(:,:),ene_pot(:)
            integer comp_energy, comp_force, comp_enepot
            integer     ::  idum

            real(kind=8),dimension(1)   ::      buffer; pointer(pbuffer,buffer)
            real(kind=8), pointer       ::      buff(:)

            type(FinnisSinclair)        ::      fs
            type(Khakshouri)            ::      kh
            real(kind=8)                ::      temperature

            pbuffer = kim_api_get_model_buffer_f(pkim,ier)
            if (ier < KIM_STATUS_OK) then
                idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                              "kim_api_get_model_buffer_f", ier)
                goto 42
            end if
            call KIM_to_F90_real_array_1d(buffer,buff,9)

            fs = FinnisSinclair_ctor( buff(1),buff(2),buff(3),buff(4),buff(5),buff(6),buff(7) )
            kh = Khakshouri_ctor( buff(8),buff(9), fs )
!             call report(kh)
!
            ! Check to see if we have been asked to compute the energy, forces, energyperatom
            !
            call kim_api_getm_compute_f(pkim, ier, &
                 "energy",         comp_energy, 1, &
                 "forces",         comp_force,  1, &
                 "particleEnergy", comp_enepot, 1 )
            if (ier.lt.KIM_STATUS_OK) then
               idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                             "kim_api_getm_compute_f", ier)
               goto 42
            end if

            ! Unpack data from KIM object: Note I have spilt this into expected and optional data
            !
            call kim_api_getm_data_f(pkim, ier,                       &
                 "numberOfParticles",   pnAtoms,         1,           &
                 "coordinates",         pcoor,           1,           &
                 "energy",              penergy,         comp_energy, &
                 "forces",              pforce,          comp_force,  &
                 "particleEnergy",      penepot,         comp_enepot )
            if (ier.lt.KIM_STATUS_OK) then
               idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                             "kim_api_getm_data_f", ier)
               goto 42
            end if
            ptemp = kim_api_get_data_f(pkim, "temperature",ier )
            if (ptemp==0) then
                !   electronic temperature is not present in the KIM API object. Should default to 0.
                temperature = 0.d0
            else
                temperature = temp
            end if
!             print *,"temperature set to ",temperature,ier,KIM_STATUS_OK

            ! Cast to F90 arrays
            !
            call KIM_to_F90_real_array_2d(coordum,coor,3,numberOfParticles)
            if (comp_force.eq.1) &
               call KIM_to_F90_real_array_2d(forcedum,force,3,numberOfParticles)
            if (comp_enepot.eq.1) &
               call KIM_to_F90_real_array_1d(enepotdum,ene_pot,numberOfParticles)



            ! Initialize potential energies, forces
            !
            if (comp_enepot.eq.1) ene_pot(1:numberOfParticles) = 0.d0
            if (comp_energy.eq.1) energy = 0.d0
            if (comp_force.eq.1)  force(1:3,1:numberOfParticles) = 0.d0

!             print *,"computeEnergyForces",comp_enepot,comp_energy,comp_force


        !---    compute energy
            if ( (comp_enepot == 1).and.(comp_energy == 1) ) then
                do ii = 1,numberOfParticles
                    Ei = ionicPotentialEnergy( kh , ii,temperature*KHAKSHOURI_BOLTZMANN , pkim )
                    energy = energy + Ei
                    ene_pot(ii) = Ei
                end do
            else if ( (comp_enepot == 1).and.(comp_energy /= 1) ) then
                do ii = 1,numberOfParticles
                    Ei = ionicPotentialEnergy( kh , ii,temperature*KHAKSHOURI_BOLTZMANN , pkim )
                    ene_pot(ii) = Ei
                end do
            else if ( (comp_enepot /= 1).and.(comp_energy == 1) ) then
                do ii = 1,numberOfParticles
                    Ei = ionicPotentialEnergy( kh , ii,temperature*KHAKSHOURI_BOLTZMANN , pkim )
                    energy = energy + Ei
                end do
            end if
        !---    compute force
            if (comp_force.eq.1) then
                do ii = 1,numberOfParticles
                    call addForce( kh, ii,temperature*KHAKSHOURI_BOLTZMANN, force(:,:) , pkim )
                end do
            end if

            ier = KIM_STATUS_OK
42          continue
            Compute_Energy_Forces_KH = ier
            return
        end function Compute_Energy_Forces_KH

    end module TB_Khakshouri




!-------------------------------------------------------------------------------
!
! Model initialization routine (REQUIRED)
!
!-------------------------------------------------------------------------------
    integer function TB_Khakshouri_F__MD_385539372793_000_init(pkim , byte_paramfile, nmstrlen, numparamfiles)
!---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        use TB_FinnisSinclair
        use TB_Khakshouri
        use KIM_API
        implicit none

    !-- Transferred variables
        integer(kind=kim_intptr), intent(in) :: pkim
        integer,                  intent(in) :: nmstrlen
        integer,                  intent(in) :: numparamfiles
        integer(kind=1),          intent(in) :: byte_paramfile(nmstrlen*numparamfiles)


    !-- Local variables
        integer(kind=kim_intptr), parameter ::  one=1
        character(len=nmstrlen) ::  paramfile_names(numparamfiles)
        real(kind=8)            ::  cutoff;         pointer(pcutoff,cutoff)
        integer                 ::  ier, idum, return_error
        integer                 ::  i, j, ii
        type(FinnisSinclair)    ::  fs
        type(Khakshouri)        ::  kh
        real(kind=8)            ::  in_A,in_beta,in_d,in_c,in_c0,in_c1,in_c2,in_Ne,in_Na


        real(kind=8)        ::      rho,Te , E,dEdrho,dEdTe,W,dWdrho
        real(kind=8),dimension(1)   ::  buffer; pointer(pbuffer,buffer)
        real(kind=8),pointer        ::  buff(:)

        ! assume all is well
        !
        return_error = KIM_STATUS_OK

        ! generic code to process model parameter file names from byte string
        do i=0,numparamfiles-1
           write(paramfile_names(i+1),'(1000a)')  &
                char(byte_paramfile(i*nmstrlen+1: &
                                    i*nmstrlen+minloc(abs(byte_paramfile),dim=1)-1))
        enddo

        ! store pointers to public methods in KIM object
        call kim_api_setm_data_f(pkim, ier,                 &
            "compute", one, loc(Compute_Energy_Forces_KH), 1,  &
            "destroy", one, loc(Destroy_KH),               1)
        if (ier < KIM_STATUS_OK) then
            idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                          "kim_api_set_data_f", ier)
            return_error = ier
            goto 1000
        end if

    !   Read in model parameters from parameter file
        open(10,file=paramfile_names(1),status="old")
        read(10,*,iostat=ier) in_A,in_beta,in_d,in_c,in_c0,in_c1,in_c2,in_Ne,in_Na
        close(10)
        if (ier /= 0) then
            idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                          "reading param file", ier)
            return_error = ier
            goto 1000
        end if
        fs = FinnisSinclair_ctor( in_A,in_beta,in_d,in_c,in_c0,in_c1,in_c2 )
        !call report(fs)
        kh = Khakshouri_ctor( in_Ne,in_Na, fs )
        !call report(fs)
!
!         print *,""
!         call report(kh)
!         print *,""


    !   store model cutoff in KIM object
        pcutoff =  kim_api_get_data_f(pkim,"cutoff",ier)
        if (ier < KIM_STATUS_OK) then
            idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                          "kim_api_get_data_f", ier)
            return_error = ier
            goto 1000
        end if
        cutoff = getCutoff(kh)


   !   store buffer to reconstruct Khakshouri model
       allocate(buff(9))
       buff = (/ in_A,in_beta,in_d,in_c,in_c0,in_c1,in_c2,in_Ne,in_Na /)
       pbuffer = loc(buff)
       call kim_api_set_model_buffer_f(pkim,pbuffer,ier)
       if (ier < KIM_STATUS_OK) then
           idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                         "kim_api_set_model_buffer_f", ier)
            return_error = ier
            goto 1000
       end if

1000   continue
       TB_Khakshouri_F__MD_385539372793_000_init = return_error
       return
    end function TB_Khakshouri_F__MD_385539372793_000_init

